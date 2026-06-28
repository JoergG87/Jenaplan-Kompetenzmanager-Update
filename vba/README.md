# VBA Framework

Dieses Verzeichnis enthält den versionierbaren VBA-Quellcode für die spätere Interaktionsschicht.

Python bleibt verantwortlich für Workbook-Erzeugung, Datenmodell, UI-Projektionen, Styles, Berichte und Fachlogik.

VBA darf ausschließlich Navigation, Buttons, Klickverhalten, Dialoge, UserForms und Benutzerinteraktion übernehmen.

Keine fachliche Logik wird in VBA implementiert.

## Packaging-Hinweis

Excel speichert VBA als binäres `vbaProject.bin`.

Die Dateien unter `vba/modules/` sind die lesbaren Quellen. Damit sie in einer `.xlsm` ausführbar werden, müssen sie in das VBA-Projekt importiert und anschließend als aktualisierter Seed gespeichert werden.

Der aktuelle technische PoC beweist, dass Python ein vorhandenes `vbaProject.bin` aus `seeds/JenaplanSeed.xlsm` erhalten und in eine generierte Arbeitsmappe übernehmen kann.

## Seed-Bereinigung

Der bereinigte Seed dient als Modulbasis. Er muss im VBA-Projekt diese Module enthalten:

- `Globals`
- `Navigation`
- `UI`

Nicht enthalten sein dürfen:

- `Modul1`
- registrierte alte Testmodule

Die Excel-Objekte des Seeds gehören zur Seed-Arbeitsmappe. Die fachlich relevanten Excel-Objekte entstehen in der generierten Framework-Datei.

Das Packaging-Skript setzt dort, soweit technisch möglich:

- Workbook-CodeName: `DieseArbeitsmappe`
- Klassenübersicht-CodeName: `wsClassOverview`
- Schülerprofil-CodeName: `wsStudentProfile`

Workbook- und Worksheet-CodeNames sind Teil des Excel-/VBA-Projekts und lassen sich nur begrenzt durch Python kontrollieren. Sie müssen bei Bedarf manuell im VBA-Editor geprüft werden.

Das Packaging-Skript prüft den Seed vor dem Erzeugen des PoC. Wenn die Module `Globals`, `Navigation` und `UI` fehlen oder `Modul1` noch registriert ist, wird keine neue `.xlsm` erzeugt.
