# Projektdokumentation: Jenaplan-Kompetenzmanager

## Aktueller Produktstand

Der Jenaplan-Kompetenzmanager ist eine lokale Python-/PySide6-Desktop-Anwendung fuer Lehrkraefte. PySide ist die aktive Produktoberflaeche, SQLite die produktive lokale Datenhaltung.

Der implementierte Stand nach Sprint 10B und den anschliessenden Schuelerprofil-UX-Korrekturen umfasst die zentralen Arbeitsbereiche fuer Stammdaten, Unterrichtsalltag, Beobachtung, Kompetenzdokumentation, Schuelerprofil, Lernentwicklungsbericht und Lernentwicklungsgespraech. Unveraenderliche Bericht- und LEG-Revisionen sowie daraus erzeugte PDF-Artefakte sind produktiv umgesetzt.

Das Projekt befindet sich in der **Produktreifephase**. Der Schwerpunkt liegt auf Konsistenz, Barrierearmut, Pilotierbarkeit, Dokumentationsqualitaet, Betriebsentscheidungen und Release-Vorbereitung. Fuer den technischen macOS-Pilotbuild ist die Paketversion `0.1.0` festgelegt; daraus folgt noch keine allgemeine Produktrelease- oder App-Store-Entscheidung.

Excel/VBA ist eine historische Vorstufe. Die damalige Workbook-Linie wird unter `legacy/excel/` als Referenz erhalten, ist aber weder Zielplattform noch aktiver Produktpfad. Historische Workbook-Versionen wie `v0.4` und fruehere Ausgabedateien sind keine aktuellen Hauptartefakte.

## Projektziel

Der Kompetenzmanager unterstuetzt Lehrkraefte an Jenaplan-Grundschulen bei der strukturierten, nachvollziehbaren und alltagstauglichen Dokumentation von Lernentwicklung nach dem Thueringer Lehrplan.

Das Produkt soll den Dokumentationsaufwand reduzieren, ohne paedagogische Entscheidungen zu automatisieren. Beobachtungen, bestaetigte Kompetenzstaende, Berichte und Lernentwicklungsgespraeche bleiben fachlich unterscheidbare Arbeits- und Ausgabekontexte.

## Paedagogische Leitlinien

- Beobachtung steht vor Bewertung.
- Dokumentierte Ereignisse bleiben bis zum konkreten Beleg nachvollziehbar.
- Entwicklung wird aus realen Beobachtungen und Bestaetigungen sichtbar, nicht aus erfundenen Zwischenwerten.
- Fehlende Dokumentation ist kein negativer Leistungsstatus.
- Automatische Projektionen liefern Orientierung, aber keine fertigen paedagogischen Aussagen.
- Lehrkraefte verantworten manuelle Berichtstexte, Gespraechsinhalte und bewusste Evidenzauswahl.
- Status, Dokumentationsabdeckung und Entwicklung duerfen nicht allein durch Farbe vermittelt werden.

## Abgeschlossene Kernfunktionen

### Stammdaten und Unterrichtskontext

- persistente Schueler-, Stammgruppen-, Kurs- und Kursverbundverwaltung
- stabile technische IDs und kontrollierte Archivierungs- beziehungsweise Aktivitaetsregeln
- persistenter Wochenstundenplan mit Stammgruppen-, Kurs- und Kursverbundkontext
- read-only Dashboard `Heute` mit aktueller beziehungsweise naechster Stunde, Tagesverlauf, Dokumentationsorientierung und direkten Arbeitswegen

### Beobachtungen und Dokumente

- Beobachtungen mit Datum, Kontext, Notiz, Kompetenzzuordnung und Einzelbewertungen
- Schnellbeobachtungen ohne erzwungene Kompetenzzuordnung
- Bearbeiten und Soft Delete ueber den bestehenden Application-/Repository-Pfad
- studentenzentrierte Dokument- und Medienreferenzen ohne Datei-BLOBs in SQLite
- historisch sichere Darstellung nicht mehr aktiver oder nicht mehr verfuegbarer Referenzen

### Schuelerprofil und Kompetenzen

- kindbezogener Arbeitsraum mit dauerhaft sichtbarem Schuelerkontext
- Profilueberblick nach der produktiven Variante-A-UX
- dokumentationsbezogene Orientierungskarten, Kompetenzuebersicht, neueste Beobachtungen und neutrale Hinweise auf noch nicht dokumentierte Bereiche
- Kompetenz-Cockpit mit der Hierarchie `Fach -> Kompetenzbereich -> Thema -> Kompetenz`
- kanonische Trennung von bestaetigtem Stand, berechnetem Vorschlag und Beobachtungsevidenz
- Maus-, Tastatur-, Fokus- und Accessibility-Vertraege fuer zentrale Profilinteraktionen

### Lernentwicklungsbericht

- persistenter bearbeitbarer Berichtsentwurf `RPD`
- bewusst ausgewaehlte Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen
- manuell verantwortete Gesamt- und Fachtexte
- stabiles Berichtaggregat `RPT` mit unveraenderlichen Revisionen `RPV`
- snapshotbasierte historische Leseansicht mit Integritaetspruefung
- unveraenderliches finales PDF-Artefakt `RPA` genau einer aktuellen finalisierten Revision

### Lernentwicklungsgespraech

- persistenter, live-referenzierender LEG-Arbeitsentwurf `LCD`
- phasenorientierter Arbeitsraum fuer Vorbereitung, Gespraech und gemeinsam festgehaltene Ergebnisse
- bewusst ausgewaehlte Kompetenz- und Beobachtungsbelege
- stabiles LEG-Aggregat `LCF` mit unveraenderlichen Revisionen `LCV`
- snapshotbasierte historische Leseansicht mit Integritaetspruefung
- unveraenderliches finales PDF-Artefakt `LCA` genau einer aktuellen abgeschlossenen Revision

## Aktive Systemarchitektur

Die aktive Schichtenfolge lautet:

```text
PySide UI
-> ViewModels
-> Desktop Adapter
-> Application Commands und Queries
-> Domain Services und Validatoren
-> Repositories
-> SQLite
```

Fuer Ausgaben gilt zusaetzlich:

```text
verifizierter fachlicher Snapshot
-> renderer-neutrales Ausgabemodell
-> reiner PDF Renderer
-> unveraenderliche Datei und Artefaktreferenz
```

Fuer den lokalen macOS-Pilotbetrieb gilt:

```text
signiertes oder ad-hoc signiertes App-Bundle
-> unveraenderliche eingebettete Laufzeit und Ressourcen
-> getrennter Benutzerpfad unter ~/Library/Application Support/
-> SQLite, Dokumente, Exporte, Backups und Logs ausserhalb der App
```

Der Apple-Silicon-Pilotbuild wird reproduzierbar mit PyInstaller erzeugt und setzt macOS 13 voraus. Die Standardvariante enthaelt keine Schuelerdaten. Ein Update ersetzt nur die `.app`; es gibt bewusst keinen Auto-Updater.

### Architekturprinzipien

- Widgets enthalten keine Businesslogik und greifen nicht direkt auf SQLite zu.
- SQLite und die dokumentierten Datenquellen bilden die fachliche Source of Truth.
- Repositories kapseln Persistenz; Application- und Domain-Schichten verantworten Schreibprozesse und Validierung.
- ViewModels und Adapter liefern displayfertige Projektionen, ohne fachliche Daten in der UI neu zu berechnen.
- Jede Funktion besitzt eine Implementierung, kann aber mehrere Einstiegspunkte haben.
- Schuelerprofil, Bericht und LEG verwenden dieselbe kanonische Kompetenz- und Evidenzprojektion, ohne eigene Statuslogik zu entwickeln.
- Historische Snapshots werden vor jeder Lese- oder PDF-Projektion gegen ihren gespeicherten SHA-256 geprueft.
- `PdfRenderer` kennt weder SQLite noch Repositories, Draftstatus oder fachliche Freigaberegeln.
- Bericht und LEG bleiben getrennte fachliche Domains mit getrennten Aggregaten, Revisionen und Artefakten.
- Schema- und Datenmodellveraenderungen erfolgen nur nach Product-Owner-, Datenmodell- und Architekturreview.

## Datenhaltung und Dateien

- Produktive lokale Datenbank: `data/kompetenzmanager.sqlite`
- Lehrplanbasierter Kompetenzkatalog: `data/curriculum_catalog_v1.csv`
- Konfiguration und Farbreferenzen: strukturierte Dateien unter `data/`
- Verwaltete Schuelerdokumente: `data/documents/<student_id>/`
- Finale Berichtartefakte: `data/documents/<student_id>/reports/<RPT>/<RPV>/`
- Finale LEG-Artefakte: `data/documents/<student_id>/learning_conferences/<LCF>/<LCV>/`

SQLite speichert fuer Dokumente und PDF-Ausgaben Metadaten und Referenzen. Dateien werden nicht als BLOB in der Datenbank gespeichert. Produktive Beziehungen verwenden stabile IDs und nicht sichtbare Namen oder UI-Positionen.

## Produkt- und Ausgabemodell

### Schuelerprofil

Das Schuelerprofil ist eine aktuelle Live-Arbeitsansicht. Es zeigt dokumentierte Staende, Evidenz, Dokumentationsabdeckung und Arbeitswege, ist aber kein offizielles oder eingefrorenes Dokument.

### Bericht

Der Berichtsentwurf bleibt bearbeitbar und live-referenzierend. Eine bewusste Finalisierung erzeugt beziehungsweise aktualisiert ein stabiles Berichtaggregat und schreibt eine neue unveraenderliche Revision. Korrekturen erfolgen als Folgerevision; fruehere Revisionen bleiben historisch lesbar.

### Lernentwicklungsgespraech

Der LEG-Entwurf bleibt ein eigener bearbeitbarer Gespraechsarbeitsstand. Ein expliziter Abschluss friert ausschliesslich den reproduzierbaren Gespraechskontext, gemeinsame Ergebnisse und bewusst ausgewaehlte Belege in einer unveraenderlichen LEG-Revision ein. Interne Vorbereitung wird nicht automatisch Teil des Abschlusses.

### PDF-Artefakte

PDF ist ein Ausgabeformat und keine Fachschicht. Finale Bericht- und LEG-PDFs werden ausschliesslich aus der jeweils aktuellen, hashverifizierten Revision erzeugt. Drafts, Widgets und spaetere operative Daten sind keine Quellen eines finalen PDF-Artefakts. Ein vorhandenes Artefakt wird bei erneutem Aufruf verifiziert und nicht ueberschrieben.

## Informationsarchitektur und Design-System

Die globale Navigation trennt `ARBEIT` mit `Heute` und `Schueler` von `VERWALTUNG` mit `Stammdaten` und `Einstellungen`. Beobachtungen, Kompetenzen, Berichte und LEG bleiben ueber den Kindkontext erreichbar.

Das verbindliche PySide-Design-System ist in `docs/DESIGN_SYSTEM.md` dokumentiert. Es definiert Tokens, Typografie, Flaechen, Karten, Tabellen, Dialoge, Fokus, Reduced Motion, Tastaturbedienung und Accessibility. Historische Workbook-Layouts, feste Zellpositionen und Excel-Zoomstufen sind keine Designreferenz der aktiven Produktlinie.

Zentrale UX-Prinzipien:

- ruhige, lehrkraftzentrierte Informationshierarchie
- genau eine dominante Aktion pro Arbeitskontext
- ganze sinnvolle Zeilen und Karten als ausreichend grosse Interaktionsflaechen
- progressive Disclosure fuer Evidenz und historische Details
- sichtbare Fokuszustaende und vollstaendige Tastaturwege
- Status nie ausschliesslich ueber Farbe
- responsive Desktop-Zielgroessen 1180 x 760, 1280 x 800 und 1400 x 900

## Prototypen und Product Discovery

In `prototypes/` abgelegte UX-Studien sind isolierte Entscheidungs- und Referenzartefakte. Sie verwenden fiktive Daten und werden erst nach ausdruecklicher Produktentscheidung in die produktive App uebertragen. Ein Prototyp ist weder Datenquelle noch produktive Nebenanwendung.

## Historische Excel-/VBA-Linie

Die fruehere Excel-/Workbook-Architektur, VBA-Interaktionsschicht, UserForm- und Worksheet-Dialogspikes sowie die historische Version `v0.4` bleiben als Projektgeschichte dokumentiert. Ausfuehrbare Altstaende und Quellen liegen unter `legacy/excel/`.

Fuer die aktive Produktlinie gilt:

- keine neuen Excel- oder VBA-Funktionen
- keine Workbook-Datei als aktuelles Hauptartefakt
- keine VBA-/AppleScript-Smoke-Tests als Standardpruefung
- Excel/openpyxl nur bei ausdruecklichem Legacy- oder Exportauftrag

Historische Sprint- und ADR-Texte bleiben als damaliger Entscheidungsstand lesbar, werden aber als historisch oder durch die PySide-/SQLite-Linie abgeloest gekennzeichnet.

## Dokumentationssystem

- `PROJECT.md`: aktueller Produktstand und dauerhafte Projektgrundlagen
- `SPRINTS.md`: operative Planung und historisch gekennzeichnete Sprintstaende
- `DECISIONS.md`: Architekturentscheidungen und ihr Umsetzungsstatus
- `CHANGELOG.md`: chronologische Aenderungen ohne Vorwegnahme einer Release-Version
- `docs/PROJECT_CONSTITUTION.md`: verbindliche Projektverfassung
- `docs/TECHNICAL_NAMES.md`: technische Namen und IDs
- `docs/DATA_REGISTRY.md`: Datenquellen und Persistenzobjekte
- `docs/DATA_LIFECYCLE.md`: Schreib-, Historien- und Loeschprozesse
- `docs/VIEW_DATA_OWNERSHIP.md`: Owner und Quellen der Ansichten
- `docs/UI_DATA_MAPPING.md`: sichtbare UI-Felder und ihre Datenquellen
- `docs/DESIGN_SYSTEM.md`: verbindliches PySide-Design-System

Neue Architektur-Dokumente werden nur eingefuehrt, wenn eine echte Luecke nicht in den bestehenden Governance-Dokumenten geschlossen werden kann.

## Rollen und Entwicklungsreihenfolge

- Product Owner: gibt neue Funktionen, fachliche Aenderungen und Datenmodellaenderungen frei.
- Fachliche Review: prueft paedagogische Verstaendlichkeit, Lehrplanbezug und nicht bewertende Darstellung.
- UX-/Accessibility-Review: prueft Informationshierarchie, Bedienbarkeit, Tastatur, Fokus und Kontrast.
- Technische Review: prueft Architekturgrenzen, Wartbarkeit, Integritaet und Lauffaehigkeit.

Jede Implementierung folgt dieser Reihenfolge:

1. Vision
2. Product Discovery
3. Produktentscheidung
4. Datenmodell-Review
5. Architektur-Review
6. UX-Review
7. Prompt-Review
8. Implementierung
9. Technical Review
10. Test
11. Commit

## Aktueller Entwicklungsstatus

Der Funktionsaufbau bis Sprint 10B sowie die anschliessenden Schuelerprofil-UX-Korrekturen sind umgesetzt. Die aktive Phase ist die Produktreifephase.

Aktuelle Arbeitsschwerpunkte sind:

- Dokumentationskonsistenz und nachvollziehbare Produktbaseline
- fachliche und visuelle Pilotpruefung
- Accessibility- und Tastaturqualitaet
- robuste Desktop-Darstellung in den festgelegten Zielgroessen
- Packaging-, Betriebs- und Datenschutzentscheidungen
- Release-Vorbereitung ohne Vorwegnahme von Version oder Auslieferung

Weiterhin offen bleiben insbesondere Product-Owner- beziehungsweise Betriebsentscheidungen zu Rollen und Berechtigungen, Aufbewahrung und Zugriffsschutz, Archivierung und Verschluesselung, Renderer-Versionierung, mehreren Artefakten pro Revision sowie einem moeglichen gemeinsamen, klar getrennten Bericht-/LEG-Ausgabepaket.

## Definition of Done

Eine Aenderung gilt als abgeschlossen, wenn:

- die freigegebene fachliche Anforderung umgesetzt oder dokumentiert ist,
- keine Projekt- oder Architekturregel verletzt wurde,
- Datenquellen, technische Namen, Lifecycle und UI-Mapping konsistent dokumentiert sind,
- das Changelog aktualisiert wurde,
- fokussierte und risikogerechte Pruefungen erfolgreich sind,
- die PySide-Anwendung weiterhin importierbar und offscreen startbar ist,
- keine nicht freigegebene Funktion oder Datenmodellentscheidung eingefuehrt wurde.
