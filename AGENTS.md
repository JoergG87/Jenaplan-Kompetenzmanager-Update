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
- Jede Implementierung folgt der Reihenfolge: Vision, Product Discovery, Produktentscheidung, Datenmodell-Review, Architektur-Review, UX-Review, Prompt-Review, Implementierung, Technical Review, Test, Commit.
