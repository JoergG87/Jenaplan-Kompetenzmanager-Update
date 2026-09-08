# Roadmap

## Einordnung

Die Roadmap ordnet Produktphasen auf Basis des veröffentlichten Pilotstands
0.4.0 / Build 400 ein. Sie ist keine Sprintfreigabe. Konkrete Aufgaben, Status
und Abhängigkeiten stehen in `BACKLOG.md`; operative, bereits freigegebene
Arbeit steht in `SPRINTS.md`.

PySide6 ist die aktive Produktoberfläche, Final V4 auf SQLCipher 4.17 die
produktive lokale Datenbasis. Python verantwortet Datenmodell, Application- und Domain-Schicht,
Persistenz, ViewModels, Adapter, UI-Projektionen, Berichte, Exporte und
Fachlogik. Excel/VBA ist ausschließlich historische Legacy-/Referenzlinie unter
`legacy/excel/` und kein Zielpfad für neue Funktionen.

Alle Phasen bleiben den pädagogischen Leitlinien untergeordnet:

- Beobachtungen bilden die fachliche Grundlage.
- Die Software unterstützt pädagogische Entscheidungen und ersetzt sie nicht.
- Fehlende Dokumentation ist kein negativer Leistungsstatus.
- Es gibt keine automatische Benotung oder automatische Leistungsbewertung.
- Datenhaltung bleibt lokal, nachvollziehbar und verantwortbar.

## Phase 0 - Produktgrundlage bis Version 0.3.0 abgeschlossen

Der interne Releasekandidat 0.3.0 umfasst die lokale PySide6-/SQLite-Anwendung mit
Lehrplankatalog, Einzel- und Schnellbeobachtung für ein Kind, Schülerprofilen,
Kompetenz- und Dokumentationsprojektionen, Lernentwicklungsberichten,
Lernentwicklungsgesprächen, unveränderlichen Revisionen und finalen
PDF-Artefakten, Stundenplan und Dashboard, Stammdaten, Dokumenten/Medien,
Backup/Restore, lokalem Konto, Passwort und Recovery-Codes, App-Sperre,
macOS-Keychain/Touch ID, gespeicherter Geräteanmeldung, Support-Reset-Workflow,
`Erste Schritte`, Pilotdokumentation und macOS-arm64-Paket.

Diese Funktionen werden nicht mehr als Zukunftsarbeit geführt. Reale
Hardware-, Alltags- und Ergonomieprüfung bleibt Teil der nächsten Phase.

## Phase 1 - veröffentlichte Pilotbasis 0.4.0 / Build 400 und Stabilisierung

Zuerst wird der implementierte Stand unter realen Pilotbedingungen validiert.
Priorität P0 haben ausschließlich Datenverlust, fehlerhafte Speicherung,
Sicherheitsfehler, blockierte Hauptabläufe sowie starke Überlagerungen oder
abgeschnittene Kernaktionen.

Pilottestwünsche und Komfortideen werden getrennt erfasst. Sie werden nicht
allein durch ihre Nennung zu beschlossenen Produktänderungen.

Der veröffentlichte Stand 0.4.0 / Build 400 stammt unveränderlich aus Commit
`e96a77e328da98bfb3622201110e6e08c8b3e312`; der annotierte Tag
`v0.4.0-build400` zeigt auf genau diesen Commit. Er verwendet Final V4, aktive
lokale Verschlüsselung, verschlüsselte Managed Documents und
installationsgebundenes `.jkmebackup`. Individuelle Fachprofile und die
schuljahresbasierte Entwicklungsübersicht gehören zum Pilotumfang. Ebenfalls
Bestandteil dieser Basis sind:

- der vollständig implementierte Schuljahreswechsel;
- der gemeinsame sichere read-only In-App-Viewer für finale verschlüsselte
  RPA-/LCA-PDFs;
- die Profilnavigation aus `Passende Kinder für diese Stunde` mit getrennter
  Aktion `Beobachten`;
- der Beobachtungskontext `Partnerarbeit`;
- die sichtbare Stammgruppe in kombinierten Schülerlisten;
- Fachillustrationen beziehungsweise Fachvignetten.

Reale Bedien-, Hardware-, Qt-/HTML-Vergleichs- und Betriebsabnahmen bleiben von
der Implementierungs- und Veröffentlichungsfeststellung getrennt. Es gibt
keine behauptete Developer-ID-Signierung oder Notarisierung, keine
Windows-Freigabe, keinen Stable-Release und keine schulische Betriebsfreigabe.
GitHub-Pilotveröffentlichung, Pilot-Appcast, Stable, PO-Abnahme und
Notarisierung sind getrennte Gates.

### Unreleased nach Build 400

Der erste Produktfix nach Build 400,
`926582f7db3a44642b05301fbbb676a91a1f500c`, korrigiert die individuelle
Fachrelevanz der Dashboard-Heatmap und von `Passende Kinder für diese Stunde`,
ist aber noch nicht als neuer Build veröffentlicht. Die am 08.09.2026
beauftragte lokale Paketierung 0.4.1 / Build 401 ist aus `ad4bd32` erstellt.
Der Schlüsselzugriff blockiert den Erststart (`data_master_key_access_denied`);
die vollständige Paketabnahme bleibt **NO-GO**. Wiederaufnahmebedingungen
stehen in `SPRINTS.md`. Quellnachweis und Veröffentlichung bleiben getrennt.

## Phase 2 - Alltagsdaten effizient einrichten

Ziel ist, den manuellen Einrichtungsaufwand vor und zwischen Schuljahren zu
reduzieren. Planungskandidaten sind:

- Schülerlisten-Import
- Dublettenprüfung und wiederholbarer Import
- sichere Vorschau und Zuordnung importierter Kinder zu den vorhandenen
  Stammgruppen und Kursen

Die Discovery vom 07.09.2026 ist in `BACKLOG.md` abgeschlossen: lokaler
CSV-Erstimport, explizite Identität, Vorschau und eine gemeinsame Transaktion.
Als Nächstes ist der konkrete Erstumfang zu entscheiden; automatischer
Wiederholungsimport benötigt zuvor eine belastbare Quellidentität. Der
Schuljahreswechsel ist bereits Bestandteil von Build 400 und weder von diesem
Import abhängig noch erneut freizugeben.

## Phase 3 - Beobachtung im Unterricht beschleunigen

Am 07.09.2026 wurden Tastaturzugang, Weitererfassen und Eingabefokus als
kleines Komfortpaket freigegeben. Gemeinsam mit den freigegebenen
einklappbaren Berichtsfächern und dem Datensicherungshinweis werden sie in
`SPRINTS.md` mit erfolgreichen Einzeltests und Computer-Use-Abnahmen geführt.
Alle fünf sind im unveröffentlichten Quellstand implementiert. Die
Importvorbereitung ist abgeschlossen; eine Importimplementierung ist damit
nicht beschlossen.

Nach Auswertung des Pilotworkflows werden mögliche Mehrkind-Abläufe geprüft:

- Gruppenbeobachtung
- Schnellbeobachtung mehrerer Kinder beziehungsweise Gruppenbewertung
- geplante Beobachtungen
- Kompetenzvorlagen für Unterrichtssituationen

Vor Umsetzung muss entschieden werden, ob fachlich eine gemeinsame Beobachtung
oder mehrere atomar erzeugte Einzelbeobachtungen entstehen. Gemeinsame Notiz,
individuelle Bewertung, spätere Bearbeitung, Datenschutz und Fehlerrollback
sind Teil dieser Entscheidung. Es wird keine automatische Bewertung eingeführt.

## Phase 4 - Übersichten und Lernentwicklung vertiefen

Erst nach Pilottest des vorhandenen Schülerprofils, Dokumentationsstatus und
Dashboard-Heatmaps werden zusätzliche Übersichten bewertet:

- Klassenmatrix und Kursmatrix
- gruppenbezogene Dokumentationsstände
- `Zuletzt bearbeitet` auf `Heute`
- historische Kompetenz- und Entwicklungsansichten
- pädagogische Hinweise aus vorhandener Evidenz ohne automatische Bewertung

Das Dashboard bleibt stundenbezogener Arbeitsstart. Eine allgemeine
`Entwicklung sichtbar`-Analyse auf dem Dashboard wurde verworfen; neue
Analyseflächen benötigen eine eigene Produktentscheidung.

## Phase 5 - Professioneller Betrieb und Verteilung

Der produktive Support-Reset ist als lokaler Ausnahmeweg umgesetzt.
Planungskandidaten bleiben Developer-ID-Signierung und Apple-Notarisierung,
Stable-Inbetriebnahme, ein erst vor Schemaänderungen zu entscheidender
Migrationsprozess, Diagnosepaket, der bewusste
Klartextexport finaler verschlüsselter RPA-/LCA-Artefakte, geregelter
Gerätewechsel sowie eine spätere Windows-Version mit plattformeigener
Credential-Anbindung.

Diese Punkte werden getrennt priorisiert. Der manuelle DMG-Pfad und das lokale
Backup/Restore bleiben bis zum vollständigen Bestehen der Update-Release-Gates
der verbindliche Pilotpfad.

## Langfristige strategische Optionen

Mehrbenutzerbetrieb, Rollen, schulweite Installation, portable
Schlüsselwiederherstellung und Cloud-/Mehrgerätebetrieb sind langfristige
Optionen, keine beschlossenen Funktionen. Jede Option benötigt eine
eigenständige Produkt-, Datenschutz-, Bedrohungs-, Betriebs-, Datenmodell- und
Migrationsentscheidung. Die lokale Final-V4-Verschlüsselung aus Build 400 ist
umgesetzt; daraus folgt keine Freigabe für zentrale Schlüsselverwaltung oder
portable DMK-Recovery.

## Historische Produktlinie

Die frühere Excel-/Workbook-/VBA-Roadmap mit UserForms,
Worksheet-Dialogseiten, Runtime Adapter, Projection Refresh, Seeds und
AppleScript-Smoke-Tests ist abgeschlossen, archiviert oder durch ADR-046 und
ADR-047 ersetzt. Historische Details bleiben in `SPRINTS.md`, `DECISIONS.md`
und `CHANGELOG.md` erhalten; sie bilden keine aktive Roadmap. Frühere Abschnitte
in `DISCOVERY.md` und `UX_BLUEPRINT.md`, die Excel als Zielplattform oder den
ersten Prototypumfang beschreiben, sind historischer Entstehungskontext und
keine Freigabe entgegen dem aktuellen PySide6-/SQLite-Produktpfad.
