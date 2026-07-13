# Sprint 7C – UX-Prototyp Lernentwicklungsbericht

## Start

Vom Projektstamm aus:

```bash
python3 prototypes/learning_report_ux/main.py
```

Voraussetzung ist ausschließlich die bereits im Projekt verwendete Abhängigkeit `PySide6`. Der Prototyp importiert keine produktiven Projektmodule.

## Ziel und Abgrenzung

Dieser isolierte Prototyp ist eine fachliche und visuelle Gesprächsgrundlage für Jörg und Laura. Er verbindet eine Arbeitsansicht zum Zusammenstellen eines Lernentwicklungsberichts mit einer drucknahen, mehrseitigen Vorschau.

Er ist ausdrücklich keine produktive Berichtsfunktion. Es gibt keine SQLite-Verbindung, Repositorys, produktiven Adapter oder ViewModels, Migration, Tabellen, Speicherung, echte PDF-Erzeugung, Versionierung, Freigabelogik oder Integration in das Schülerprofil. Sämtlicher Zustand lebt nur für die Dauer des gestarteten Prozesses in den PySide-Widgets.

## Demo-Daten

Alle Namen und Inhalte sind fiktiv und im Quelltext klar als Demo-Daten gebündelt:

- Schülerin `Mara Beispielkind`
- Stammgruppe `Sonnenbogen`
- Lehrkraft `Laura Musterlehrerin`
- Berichtszeitraum August 2026 bis Januar 2027
- Fächer Deutsch, Mathematik, EPU und Sozialkompetenz
- fiktive Beobachtungsbelege, manuelle Berichtstexte und Dokumentationsstände
- Mathematik-Beispiel `Größen und Messen → Zeit` mit sieben getrennten konkreten Kompetenzen vom Ablesen voller Stunden bis zum Übertragen von Schreib- und Sprechweisen

Die Zahlen in den Diagrammen stellen ausschließlich Dokumentationsumfang, einzelne dokumentierte Stände oder Beobachtungsverteilung dar. Sie sind keine Leistungswerte.

## Dargestellte Interaktionen

- Wechsel zwischen `Bericht bearbeiten` und `Berichtsvorschau`
- Auswahl der vier Facharbeitsbereiche
- Ein- und Ausblenden von Gesamtblick, Fachabschnitten, Kompetenzdetails und Beobachtungsbelegen
- Auswahl konkreter Kompetenzen und ihrer Demo-Arbeitsstände
- Auswahl einzelner Beobachtungsbelege
- bewusste, standardmäßig leere Auswahl einzelner Kompetenzbereiche für Entwicklungsdarstellungen
- Bearbeiten aller pädagogischen Demo-Texte
- verzögerungsarme visuelle Aktualisierung der Vorschau
- Simulation eines professionellen mehrseitigen Dokuments
- neutraler Leerzustand, wenn keine Diagrammkompetenz gewählt ist
- einzelner Marker ohne Verbindungslinie und mit Hinweis auf die begrenzte Datenbasis bei genau einem Datenpunkt
- Verbindung ohne Trendinterpretation bei zwei Datenpunkten

## Kompetenzbereichsauswahl und Diagrammregeln

Die Auswahl `Kompetenzbereiche für Entwicklungsdarstellung` steuert nur, welche Kompetenzbereiche eine Grafik in der Vorschau erhalten. Sie verändert weder Berichtstexte noch ausgewählte konkrete Kompetenzen oder Beobachtungsbelege und ist keine pädagogische Priorisierung oder Leistungsentscheidung. Es werden keine Kompetenzbereiche automatisch vorausgewählt und keine sogenannten Schlüsselkompetenzen eingeführt.

Jeder gewählte Kompetenzbereich erhält ein eigenes kompaktes Diagramm mit vollständigem Bereichsnamen, verständlichen Bewertungsstufen, datierten Beobachtungspunkten und unterscheidbaren Markern für bestätigte Stände. Mehrere Kompetenzbereiche werden weder gemittelt noch in einer gemeinsamen oder aggregierten Linie zusammengeführt. Bei fehlender Auswahl wird kein leeres Diagramm gezeigt, bei einem Datenpunkt keine Linie gezeichnet und bei zwei Datenpunkten keine Trendinterpretation ergänzt.

Kompetenzname, Datenhinweise und Markerlegende sind umbrechende Texte außerhalb der Zeichenfläche. Die Diagramme besitzen eine ausreichende Mindesthöhe; Vorschauseiten dürfen sich dynamisch verlängern. Die simulierte A4-Ansicht bleibt innerhalb ihrer Seitenbreite, während schmale App-Fenster die Vorschau scrollbar zugänglich halten. Eine endgültige PDF-Paginierung ist ausdrücklich nicht Bestandteil des Prototyps.

## Abgrenzung zum späteren LEG-Prototyp

Dieser Prototyp bleibt ausschließlich ein Lernentwicklungsbericht für professionelle, adressatengerechte Dokumentation und eine spätere PDF-Ausgabe. Gesprächsnotizen, Elternfragen, Gesprächsagenda, Teilnehmerverwaltung, Vereinbarungsprotokoll, Gesprächsergebnis und Gesprächsabschluss gehören in einen späteren, getrennten LEG-Prototyp und werden hier nicht ergänzt.

Eine interne Abschlussnotiz ist absichtlich nicht Bestandteil der Vorschau.

## Bewusst offene Entscheidungen

Der Prototyp trifft keine Vorentscheidung über:

- finales Datenmodell und technische Entitätsnamen
- Persistenz und Versionierung
- Freigabeworkflow und Rollen/Berechtigungen
- echte PDF-Technologie und Archivierung
- endgültige schulische Pflichtfelder
- endgültige Diagramm-, Auswahl- und Layoutregeln
- verbindliche Bewertungsstufen und deren spätere Datenherkunft
- genaue Regeln für eingefrorene Ausgabestände

## Vollständig entfernbare Dateien

Der isolierte Prototyp besteht aus:

- `prototypes/learning_report_ux/main.py`
- `prototypes/learning_report_ux/demo_data.py`
- `prototypes/learning_report_ux/README.md`

Das Verzeichnis `prototypes/learning_report_ux/` kann nach dem Review vollständig entfernt werden. Es bestehen keine Imports oder Verweise aus der produktiven Anwendung in dieses Verzeichnis.
