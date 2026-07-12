# Sprint 7E - isolierter Prototyp der PDF-Engine

## Zweck

Dieser Prototyp validiert die technische Ausgabe-Architektur für professionelle pädagogische PDF-Dokumente. Er ist eine eigenständige Python-Anwendung und nicht in die produktive PySide-/SQLite-Anwendung integriert.

Das Demo-Dokument ist ein siebenseitiger `Lernentwicklungsbericht` für die fiktive Schülerin Mara Beispielkind. Alle Inhalte sind statisch vorbereitete, frei erfundene Ausgabedaten.

## Architektur und Datenfluss

```text
demo_data.py
    erstellt ein vollständiges ReportOutputModel
        -> renderer.py
            rendert neutrale Seiten und Blöcke mit ReportLab
                -> output/pdf/Sprint_7E_Lernentwicklungsbericht_Mara_Beispielkind.pdf
```

`output_models.py` enthält unveränderliche Dataclasses für Dokumentmetadaten, Seiten, Überschriften, Texte, Tabellen, Bildplatzhalter, Signaturbereiche und Diagrammdaten. Das Modell enthält damit bereits alle Informationen, die zur Ausgabe benötigt werden.

`renderer.py` kennt nur diese neutralen Ausgabeklassen. Er liest keine Datenbank, importiert keine Produktmodule, filtert keine Inhalte und berechnet oder interpretiert keine Kompetenzen, Beobachtungen oder Bewertungen.

## Wiederverwendbare Diagrammkomponenten

- `DocumentationCoverageChart` zeichnet ausschließlich übergebene Werte `dokumentiert von gesamt`.
- `CompetencyTimelineChart` zeichnet ausschließlich übergebene datierte Marker. Punkte werden nicht verbunden; es gibt keine Trendlinie, keinen Score und keine automatische Interpretation.
- `ObservationTimelineChart` ordnet ausschließlich übergebene Belege chronologisch an.

Die Diagrammkomponenten erhalten vollständige Darstellungsdaten. Auswahl, Aggregation und fachliche Bedeutung müssen vor dem Aufbau des Outputmodells feststehen.

## Beispielausgabe

Vom Projektstamm aus:

```bash
python3 prototypes/pdf_engine/main.py
```

Alternativer Zielpfad:

```bash
python3 prototypes/pdf_engine/main.py --output /tmp/lernbericht.pdf
```

Voraussetzung ist `reportlab`. Die Standardausgabe entsteht unter:

```text
output/pdf/Sprint_7E_Lernentwicklungsbericht_Mara_Beispielkind.pdf
```

Das Dokument enthält genau diese Seiten:

1. Deckblatt mit Logo-Platzhalter und Dokumentkontext
2. Pädagogischer Gesamtblick mit langem manuellem Beispieltext
3. Mathematik mit sieben konkreten Kompetenzen zu `Größen und Messen > Zeit`
4. Dokumentationsabdeckung und datierte Kompetenzstände
5. Beobachtungsbelege mit Zeitachse, Datum, Kontext und Notiz
6. Ziele und Unterstützung
7. Abschluss mit Datum, Freigabeplatzhalter und Unterschriftenbereich

## Spätere Integration

Eine spätere produktive Projektion kann Daten aus freigegebenen Application-, Domain- und Persistenzpfaden lesen, fachlich auswählen und daraus ein vollständiges `ReportOutputModel` bauen. Erst dieses eingefrorene, neutrale Modell wird an den Renderer übergeben.

Die Integrationsgrenze lautet damit:

```text
produktive Fach- und Projektionsschichten
    -> zukünftiger OutputModel-Builder
        -> ReportOutputModel
            -> PdfRenderer
                -> PDF-Datei
```

Der Prototyp implementiert den zukünftigen Builder ausdrücklich nicht.

## Bewusste Grenzen

- keine SQLite-Verbindung, Migration oder Tabelle
- keine Produktimporte, Adapter, Services, Repositories oder ViewModels
- keine PySide-Oberfläche
- keine Speicherung, Versionierung oder Archivierung fachlicher Dokumente
- kein Freigabeworkflow, keine Benutzerverwaltung und keine Exportverwaltung
- keine automatische Auswahl, Filterung, Aggregation oder Interpretation
- keine Berichts-, LEG- oder Kompetenzfachlogik
- keine Änderung am Datenmodell der produktiven Anwendung

Offen bleiben unter anderem verbindliche Corporate-Fonts und Logo-Dateien, Barrierefreiheit/PDF-UA, verbindliche Datenschutztexte, Freigabe- und Signaturregeln, Seitentrennung bei dynamischen Berichten sowie die spätere Verantwortung für den produktiven OutputModel-Builder.
