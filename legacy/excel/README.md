# Excel/VBA Legacy Archive

Dieses Verzeichnis enthaelt alte Excel-Prototypen, Workbook-Builder, VBA-Quellen, Seed-Arbeitsmappen und Hilfsskripte aus der fruehen Projektphase.

Status:

- PySide/SQLite ist die aktive Hauptanwendung.
- SQLite ist die produktive lokale Source of Truth.
- Diese Excel-/VBA-Dateien sind nicht Teil des aktiven App-Pfads.
- Neue Features werden nicht mehr in Excel, openpyxl oder VBA umgesetzt.
- Der alte Workbook-Build ist kein Pflichtcheck mehr.

Die Dateien bleiben hier historisch nachvollziehbar, falls spaeter ein expliziter Legacy- oder Exportauftrag darauf Bezug nimmt. Runtime-Dateien aus `output/` gehoeren nicht in dieses Archiv und werden nicht versioniert.

Archivierte Testdateien sind absichtlich nicht nach dem aktiven `test_*.py`-Muster benannt, damit `python3 -m pytest` nur die PySide-/SQLite-Linie prueft.
