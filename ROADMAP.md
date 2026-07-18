# Roadmap

## Einordnung

Die Roadmap ordnet Produktphasen nach Version 0.2. Sie ist keine
Sprintfreigabe. Konkrete Aufgaben, Status und Abhängigkeiten stehen in
`BACKLOG.md`; operative, bereits freigegebene Arbeit steht in `SPRINTS.md`.

PySide6 ist die aktive Produktoberfläche, SQLite die produktive lokale
Datenbasis. Python verantwortet Datenmodell, Application- und Domain-Schicht,
Persistenz, ViewModels, Adapter, UI-Projektionen, Berichte, Exporte und
Fachlogik. Excel/VBA ist ausschließlich historische Legacy-/Referenzlinie unter
`legacy/excel/` und kein Zielpfad für neue Funktionen.

Alle Phasen bleiben den pädagogischen Leitlinien untergeordnet:

- Beobachtungen bilden die fachliche Grundlage.
- Die Software unterstützt pädagogische Entscheidungen und ersetzt sie nicht.
- Fehlende Dokumentation ist kein negativer Leistungsstatus.
- Es gibt keine automatische Benotung oder automatische Leistungsbewertung.
- Datenhaltung bleibt lokal, nachvollziehbar und verantwortbar.

## Phase 0 - Produktgrundlage bis Version 0.2 abgeschlossen

Der Pilot-Release-Kandidat 0.2 umfasst die lokale PySide6-/SQLite-Anwendung mit
Lehrplankatalog, Einzel- und Schnellbeobachtung für ein Kind, Schülerprofilen,
Kompetenz- und Dokumentationsprojektionen, Lernentwicklungsberichten,
Lernentwicklungsgesprächen, unveränderlichen Revisionen und finalen
PDF-Artefakten, Stundenplan und Dashboard, Stammdaten, Dokumenten/Medien,
Backup/Restore, lokalem Konto, Passwort und Recovery-Codes, App-Sperre,
macOS-Keychain/Touch ID, gespeicherter Geräteanmeldung, Support-Reset-Workflow,
`Erste Schritte`, Pilotdokumentation und macOS-arm64-Paket.

Diese Funktionen werden nicht mehr als Zukunftsarbeit geführt. Reale
Hardware-, Alltags- und Ergonomieprüfung bleibt Teil der nächsten Phase.

## Phase 1 - Pilottest 0.2 und Stabilisierung

Zuerst wird der implementierte Stand unter realen Pilotbedingungen validiert.
Priorität P0 haben ausschließlich Datenverlust, fehlerhafte Speicherung,
Sicherheitsfehler, blockierte Hauptabläufe sowie starke Überlagerungen oder
abgeschnittene Kernaktionen.

Pilottestwünsche und Komfortideen werden getrennt erfasst. Sie werden nicht
allein durch ihre Nennung zu beschlossenen Produktänderungen.

## Phase 2 - Alltagsdaten effizient einrichten

Ziel ist, den manuellen Einrichtungsaufwand vor und zwischen Schuljahren zu
reduzieren. Planungskandidaten sind:

- Schülerlisten-Import
- Dublettenprüfung und wiederholbarer Import
- Schuljahreswechsel, Versetzung und kontrollierte Archivierung
- Übernahme von Stammgruppen, Kursen und Kursverbünden

Empfohlene Reihenfolge: zuerst ein Discovery-/Architecture-Gate für den
Schülerlisten-Import, danach erst eine Implementierungsentscheidung. Der
Schuljahreswechsel baut auf den Import-, Historien- und Archivierungsregeln auf
und ist nicht gleichzeitig freigegeben.

## Phase 3 - Beobachtung im Unterricht beschleunigen

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
- historische Kompetenz- und Entwicklungsansichten
- pädagogische Hinweise aus vorhandener Evidenz ohne automatische Bewertung

Das Dashboard bleibt stundenbezogener Arbeitsstart. Eine allgemeine
`Entwicklung sichtbar`-Analyse auf dem Dashboard wurde verworfen; neue
Analyseflächen benötigen eine eigene Produktentscheidung.

## Phase 5 - Professioneller Betrieb und Verteilung

Planungskandidaten sind produktiver Support-Reset-Schlüssel und Supportprozess,
Developer-ID-Signierung und Apple-Notarisierung, kontrollierter Update- und
Migrationsprozess, Diagnosepaket, Backup-Erinnerung, geregelter Gerätewechsel
sowie eine spätere Windows-Version mit plattformeigener Credential-Anbindung.

Diese Punkte werden getrennt priorisiert. Der bestehende manuelle App-Austausch
und das bestehende Backup/Restore bleiben bis zu einer neuen Entscheidung der
verbindliche Pilotpfad.

## Langfristige strategische Optionen

Verschlüsselung, Mehrbenutzerbetrieb, Rollen, schulweite Installation und
Cloud-/Mehrgerätebetrieb sind langfristige Optionen, keine beschlossenen
Funktionen. Jede Option benötigt eine eigenständige Produkt-, Datenschutz-,
Bedrohungs-, Betriebs-, Datenmodell- und Migrationsentscheidung. Die App-Sperre
von Version 0.2 darf nicht als Dateiverschlüsselung dargestellt werden.

## Historische Produktlinie

Die frühere Excel-/Workbook-/VBA-Roadmap mit UserForms,
Worksheet-Dialogseiten, Runtime Adapter, Projection Refresh, Seeds und
AppleScript-Smoke-Tests ist abgeschlossen, archiviert oder durch ADR-046 und
ADR-047 ersetzt. Historische Details bleiben in `SPRINTS.md`, `DECISIONS.md`
und `CHANGELOG.md` erhalten; sie bilden keine aktive Roadmap. Frühere Abschnitte
in `DISCOVERY.md` und `UX_BLUEPRINT.md`, die Excel als Zielplattform oder den
ersten Prototypumfang beschreiben, sind historischer Entstehungskontext und
keine Freigabe entgegen dem aktuellen PySide6-/SQLite-Produktpfad.
