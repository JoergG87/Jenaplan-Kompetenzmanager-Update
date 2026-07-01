# VBA Framework

Dieses Verzeichnis enthält den versionierbaren VBA-Quellcode für die spätere Interaktionsschicht.

Python bleibt verantwortlich für Workbook-Erzeugung, Datenmodell, UI-Projektionen, Styles, Berichte und Fachlogik.

VBA darf ausschließlich Navigation, Buttons, Klickverhalten, Dialoge, UserForms und Benutzerinteraktion übernehmen.

Keine fachliche Logik wird in VBA implementiert.

## Packaging-Hinweis

Excel speichert VBA als binäres `vbaProject.bin`.

Die Dateien unter `vba/modules/` sind die lesbaren Quellen. Damit sie in einer `.xlsm` ausführbar werden, müssen sie in das VBA-Projekt importiert und anschließend als aktualisierter Seed gespeichert werden.

Der aktuelle technische PoC beweist, dass Python ein vorhandenes `vbaProject.bin` aus `seeds/JenaplanSeed.xlsm` erhalten und in eine generierte Arbeitsmappe übernehmen kann.

## Automatischer Seed-Import

`vba/modules/SeedImport.bas` ist das dauerhafte Bootstrap-Makro fuer den Seed.

Es gehoert einmalig in `seeds/JenaplanSeed.xlsm` und bleibt dort als Standardmodul erhalten.

Danach kann Codex die versionierten VBA-Quellen automatisch aktualisieren:

```bash
python3 scripts/import_vba_sources_to_seed.py
```

Der Import aktualisiert:

- `Globals`
- `Navigation`
- `UI`
- `frm_student_new`

Das Bootstrap-Modul `SeedImport` importiert sich nicht selbst. Wenn `SeedImport.bas` geaendert wird, muss diese Bootstrap-Aenderung bewusst in den Seed uebernommen werden.

Das Skript bricht ab, wenn `SeedImport` im Seed fehlt. Dadurch wird verhindert, dass Excel einen fehlenden Makroaufruf still ignoriert und der Seed unveraendert bleibt.

Seit Feature 1.2b bricht das Skript auch ab, wenn der Seed-Bootstrap noch keine UserForms korrekt erzeugen kann. Dann muss die aktuelle Datei `vba/modules/SeedImport.bas` einmalig im Seed aktualisiert und gespeichert werden; danach erzeugt das Skript `frm_student_new` automatisch als echte MSForms-UserForm.

Wichtig: Microsoft Excel fuer macOS hat den direkten Import von `vba/forms/frm_student_new.frm` als kompilierbaren Code-Stream abgelegt. Deshalb erzeugt `SeedImport` diese UserForm im Seed programmgesteuert aus der versionierten Layoutdefinition, statt die `.frm` roh in das VBA-Projekt zu importieren.

Voraussetzung in Excel:

- Der Zugriff auf das VBA-Projektobjektmodell muss vertrauenswuerdig erlaubt sein.
- Wenn Excel bei `ThisWorkbook.VBProject` den Fehler 1004 meldet, ist diese Sicherheitseinstellung noch blockiert.
- Ohne diese Freigabe kann Excel keine Module programmgesteuert loeschen oder importieren.

## Sprint 3.5 Seed-Hinweis

Sprint 3.5 erweitert die versionierten VBA-Quellen um die Navigation von Schülerkarten zum Schülerprofil.

Damit diese Änderungen in `output/Jenaplan_UX_Prototype_v0.3_VBA_Framework.xlsm` ausführbar sind, müssen die Module aus `vba/modules/` in Microsoft Excel in `seeds/JenaplanSeed.xlsm` importiert und der Seed anschließend gespeichert werden.

In dieser Umgebung steht per AppleScript nur das Ausführen vorhandener Makros zur Verfügung. Ein automatischer Import geänderter `.bas`-Quellen in das VBA-Projekt konnte deshalb nicht validiert werden.

## Seed-Bereinigung

Der bereinigte Seed dient als Modulbasis. Er muss im VBA-Projekt diese Module enthalten:

- `Globals`
- `Navigation`
- `UI`
- `SeedImport`

Nicht enthalten sein dürfen:

- `Modul1`
- registrierte alte Testmodule

Die Excel-Objekte des Seeds gehören zur Seed-Arbeitsmappe. Die fachlich relevanten Excel-Objekte entstehen in der generierten Framework-Datei.

Das Packaging-Skript setzt dort, soweit technisch möglich:

- Workbook-CodeName: `DieseArbeitsmappe`
- Stammgruppenübersicht-CodeName: `wsClassOverview`
- Schülerprofil-CodeName: `wsStudentProfile`

Workbook- und Worksheet-CodeNames sind Teil des Excel-/VBA-Projekts und lassen sich nur begrenzt durch Python kontrollieren. Sie müssen bei Bedarf manuell im VBA-Editor geprüft werden.

Das Packaging-Skript prüft den Seed vor dem Erzeugen des PoC. Wenn die Module `Globals`, `Navigation` und `UI` fehlen oder `Modul1` noch registriert ist, wird keine neue `.xlsm` erzeugt.

Das Import-Skript prüft zusaetzlich, ob `SeedImport` im Seed vorhanden ist, bevor es die versionierten Module aktualisiert.

## Navigationsstandard

Spaetere Absprungpunkte folgen immer demselben Muster:

```text
Shape
-> Named Range / Slot-ID
-> technische ID
-> zentrale VBA-Funktion
-> Zielansicht
```

VBA darf dabei nur Interaktion und Navigation umsetzen. Die fachliche Bedeutung der ID kommt aus dem Datenmodell und der UI-Projektion.

### Student

- Shape: `ui_nav_student_card_XX`
- Slot-ID: `ui_student_slot_id_XX`
- technische ID: `student_id`
- zentrale Funktion: `OpenStudentProfileById(student_id)`

### Competency

- Shape: `ui_nav_competency_card_XX`
- Slot-ID: `ui_competency_slot_id_XX`
- technische ID: `competency_id`
- zentrale Funktion: `OpenCompetencyById(competency_id)`

### Report

- Shape: `ui_nav_report_card_XX`
- Slot-ID: `ui_report_slot_id_XX`
- technische ID: `report_id`
- zentrale Funktion: `OpenReportById(report_id)`

### Subject

- Shape: `ui_nav_subject_card_XX`
- Slot-ID: `ui_subject_slot_id_XX`
- technische ID: `subject_id`
- zentrale Funktion: `OpenSubjectById(subject_id)`

## Build-Hygiene

`seeds/JenaplanSeed.xlsm` ist das dauerhafte Seed-Artefakt für das VBA-Packaging.

`vba/modules/` enthält die versionierten VBA-Quellen.

Dateien unter `output/` sind erzeugte Build-Artefakte und werden nicht als Quellcode versioniert.
