# AGENTS

## Projektregeln

- Python erzeugt Workbook, Datenstruktur, Styles und Build-Artefakte.
- Python bleibt verantwortlich für Datenmodell, UI-Projektionen, Berichte und Fachlogik.
- VBA nach erfolgreichem Packaging ausschließlich für Navigation, Buttons, Dialoge, Benutzerinteraktion und UserForms verwenden.
- Keine fachliche Logik in VBA.
- VBA-Quellen unter vba/ versionieren; ausführbares VBA bleibt Bestandteil eines validierten .xlsm-Seeds.
- Zielplattform ist Microsoft Excel für macOS.
- openpyxl verwenden.
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
- Wenn VBA geändert wurde: .bas-Quellen prüfen, Seed aktualisieren, Build erzeugen, xl/vbaProject.bin prüfen und eingebetteten VBA-Code prüfen.
- Jede Implementierung folgt der Reihenfolge: Vision, Product Discovery, Produktentscheidung, Datenmodell-Review, Architektur-Review, UX-Review, Prompt-Review, Implementierung, Technical Review, Test, Commit.
