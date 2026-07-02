# AGENTS

## Projektregeln

- PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.
- SQLite ist die produktive lokale Datenbasis.
- Neue Features immer zuerst als PySide-/SQLite-Funktion denken.
- Python bleibt verantwortlich für Datenmodell, Application Layer, Domain Layer, Persistenz, ViewModels, Adapter, UI-Projektionen, Berichte, Exporte und Fachlogik.
- Keine Businesslogik in PySide-Widgets.
- Keine direkte SQLite-Logik in Qt-Widgets; Zugriff laeuft ueber Adapter, Services, Repositories und SQLite.
- Excel/openpyxl nur anfassen, wenn ausdruecklich Export, Legacy oder Altstand angefordert ist.
- Keine neuen Excel-/VBA-Features.
- Keine AppleScript-/VBA-Smoke-Tests als Zielpfad.
- VBA-Quellen unter vba/ bleiben historisch versioniert; ausfuehrbares VBA bleibt Bestandteil alter validierter .xlsm-Seeds.
- Excel/VBA ist Legacy-/Export-/Referenzpfad, nicht Hauptanwendung.
- Keine festen Zellreferenzen.
- Strukturierte Tabellen bevorzugen.
- Datenmodell niemals ohne Rücksprache ändern.
- Datenmodell niemals durch UI-Tabellen, Formeln, Hilfstabellen oder VBA umgehen.
- Alle Ansichten sind Projektionen des Datenmodells.
- Jede Änderung muss im Changelog dokumentiert werden.
- Jede Version muss lauffähig bleiben.
- Neue Funktionen nur nach Freigabe durch den Product Owner.
- Architekturentscheidungen werden in DECISIONS.md dokumentiert.
- Die zentrale Projektdokumentation wird in PROJECT.md gepflegt.
- Vor jeder Implementierung und vor jeder Codeänderung prüfen: docs/PROJECT_CONSTITUTION.md, docs/TECHNICAL_NAMES.md, docs/DATA_REGISTRY.md, docs/UI_DATA_MAPPING.md, docs/VIEW_DATA_OWNERSHIP.md, docs/DATA_LIFECYCLE.md und docs/DESIGN_SYSTEM.md.
- Keine neuen technischen Namen ohne Erweiterung von docs/TECHNICAL_NAMES.md.
- Keine neuen Datenquellen ohne Erweiterung von docs/DATA_REGISTRY.md.
- Keine neue Ansicht ohne Dokumentation in docs/VIEW_DATA_OWNERSHIP.md.
- Keine neuen UI-Felder ohne Dokumentation in docs/UI_DATA_MAPPING.md.
- Kein Schreibprozess ohne Dokumentation in docs/DATA_LIFECYCLE.md.
- Neue Funktionen erst in dieser Reihenfolge vorbereiten: PROJECT_CONSTITUTION prüfen, TECHNICAL_NAMES prüfen, DATA_REGISTRY erweitern, DATA_LIFECYCLE ergänzen, VIEW_DATA_OWNERSHIP ergänzen, UI_DATA_MAPPING ergänzen, erst danach implementieren.
- Ab Sprint 4.1 keine neuen Architektur-Dokumente einführen, außer eine echte Architektur-Lücke wird festgestellt.
- Vor neuen Dokumenten prüfen, ob die Information sinnvoll in PROJECT_CONSTITUTION, TECHNICAL_NAMES, DATA_REGISTRY, DATA_LIFECYCLE, VIEW_DATA_OWNERSHIP oder UI_DATA_MAPPING ergänzt werden kann.
- Wenn ein ausdruecklicher Legacy-/Export-Auftrag VBA beruehrt: .bas-Quellen pruefen, Seed aktualisieren, Build erzeugen, xl/vbaProject.bin pruefen und eingebetteten VBA-Code pruefen.
- Jede Implementierung folgt der Reihenfolge: Vision, Product Discovery, Produktentscheidung, Datenmodell-Review, Architektur-Review, UX-Review, Prompt-Review, Implementierung, Technical Review, Test, Commit.
