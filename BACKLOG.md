# Product Backlog

Das Product Backlog enthält fachliche Ideen, zukünftige Erweiterungen und Verbesserungsvorschläge.

Ein Eintrag im Backlog bedeutet ausdrücklich nicht, dass diese Funktion bereits geplant oder freigegeben ist.

Die Priorisierung erfolgt durch den Product Owner.

Das Backlog wird nach Epics gegliedert.

## Epic: Beobachtungen

### Gruppenbeobachtungen

Priorität: Hoch

Beschreibung:

Eine Beobachtung soll mehreren Schülerinnen und Schülern gleichzeitig zugeordnet werden können.

Status:

Idee

### Schnellbeobachtung

Priorität: Hoch

Beschreibung:

Mehrere Schueler sollen spaeter in einer Maske bewertet oder beobachtet werden koennen.

Hintergrund:

Laura nutzt aktuell ein Arbeitsblatt mit Schuelern in Spalte 1 und fortlaufenden Wertungen.

Abgrenzung:

Nicht Bestandteil von Sprint 5.

Status:

Idee

### Beobachtungsdialog

Priorität: Hoch

Beschreibung:

Neue Beobachtungen sollen spaeter ueber einen zentralen Dialog mit Datum, Kontext, Kompetenzen, Bewertung, Notiz sowie Dokumenten und Medien erfasst werden.

Offener UX-Punkt:

In der Bewertungsliste des Beobachtungsdialogs spaeter pruefen, ob Kompetenznamen fett dargestellt werden sollen. Aktuell wird keine Fettung umgesetzt, weil die Bedienung nach manuellem Test funktioniert.

Abgrenzung:

Nicht Bestandteil von Sprint 5. Kompetenzen muessen vor Umsetzung fachlich geklaert werden.

Status:

Idee

### Kompetenzzuordnung im Beobachtungsdialog

Priorität: Hoch

Beschreibung:

Beobachtungen sollen spaeter einer oder mehreren Kompetenzen zugeordnet werden.

Abgrenzung:

Nicht Bestandteil von Sprint 5.

Status:

Idee

### Kompetenzstand-Bestaetigung fachlich validieren und ausbauen

Priorität: Hoch

Beschreibung:

Die App berechnet im Schuelerprofil einen Kompetenzstand-Vorschlag aus aktiven Beobachtungen. Die Lehrkraft kann den Vorschlag als bestaetigten Kompetenzstand speichern oder manuell anpassen.

Laura-Pilottest:

- Versteht Laura `Vorschlag` als App-Berechnung?
- Ist Fach-Aufklappen in der Kompetenzuebersicht verstaendlich?
- Reicht Verlauf plus Anzahl Beobachtungen zur Nachvollziehbarkeit?
- Ist die aktuelle Bestaetigen-/Anpassen-Interaktion fuer Laura ausreichend?
- Welche Formulierung ist besser: `Vorschlag` oder `Berechneter Stand`?

Offene Folgefragen:

- Soll es eine Historie bestaetigter Kompetenzstaende geben?
- Soll der optionale Kommentar im UI sichtbar bearbeitbar werden?
- Welche Hinweise braucht Laura, wenn neue Beobachtungen nach einer Bestaetigung vorliegen?

Status:

Basis umgesetzt; fachliche Validierung offen

### Gruppenbewertung

Priorität: Hoch

Beschreibung:

Mehrere Schueler erhalten in einem gefuehrten Eingabefluss Wertungen, ohne fuer jedes Kind einzeln einen vollstaendigen Dialog zu oeffnen.

Status:

Idee

### Beobachtungsverlauf filtern

Priorität: Mittel

Status:

Idee

### Fachanzeige bei fachuebergreifenden Beobachtungen

Priorität: Offen

Beschreibung:

Entschieden: Beobachtungen mit Kompetenzbewertungen aus mehreren Faechern zeigen im Schuelerprofil `Fächerübergreifend`.
Die einzelnen Kompetenzbewertungen behalten ihr jeweiliges Fachlabel.

Abgrenzung:

Keine Schema-Migration und keine Veraenderung gespeicherter Kompetenzbewertungen.

Status:

Entschieden

### Vorbereitung geplanter Beobachtungen

Priorität: Hoch

Status:

Idee

### Kompetenzvorlagen für Unterrichtssituationen

Priorität: Mittel

Status:

Idee

### Vorschläge für Kompetenzstände

Priorität: Mittel

Status:

Idee

### Mehrere Ansichten auf Beobachtungsverläufe

Priorität: Mittel

Status:

Idee

## Epic: Schülerprofil

Platzhalter für zukünftige Einträge.

## Epic: Dokumente und Medien

### Dokument-Upload

Priorität: Offen

Beschreibung:

Dokumente sollen spaeter studentenzentriert abgelegt und in Excel nur als Referenz mit Metadaten gefuehrt werden.

Abgrenzung:

Nicht Bestandteil von Sprint 5.

Status:

Idee

### Medienvorschau

Priorität: Offen

Beschreibung:

Medien und Dokumente sollen spaeter aus dem Kompetenzmanager heraus sichtbar oder oeffenbar gemacht werden.

Abgrenzung:

Nicht Bestandteil von Sprint 5.

Status:

Idee

## Epic: Schülerverwaltung

### UX-Review Feature 1 `Neuer Schueler`

Priorität: Hoch

Beschreibung:

Das Blatt `Feature 1 – Neuer Schüler` in `output/Jenaplan_UX_Prototype_v0.1.xlsx` muss vor der technischen Dialogseiten-Umsetzung mit Laura bzw. dem Product Owner reviewed und freigegeben werden.

Abgrenzung:

Der UX-Prototyp ist keine technische Implementierung. Keine Validierung, keine Adapter-Anbindung und keine fachliche Speicherlogik.

Status:

Vor Umsetzung offen

### Worksheet-Dialogseite `dlg_neuer_schueler` nach UX-Freigabe ausbauen

Priorität: Hoch

Beschreibung:

Die worksheet-basierte Dialogseite `dlg_neuer_schueler` soll moeglichst 1:1 nach dem freigegebenen UX-Prototyp-Blatt `Feature 1 – Neuer Schüler` ausgebaut werden.

Abgrenzung:

Designentscheidungen werden im UX-Prototyp getroffen. Validierung, Adapter-Anbindung und fachliche Logik folgen erst nach der UI-Umsetzung.

Status:

Idee

### Deprecated: VBA-UserForm `frm_student_new`

Priorität: Keine aktive Umsetzung

Beschreibung:

`frm_student_new` bleibt als experimenteller Artefaktstand erhalten, wird aber wegen macOS-Kompatibilitaetsproblemen nicht mehr als primaerer Feature-1-Eingabedialog verfolgt.

Abgrenzung:

Keine weiteren AppleScript-Tests mit `do Visual Basic`. Keine produktive UserForm-Anbindung.

Status:

Deprecated

### CLI-/Python-Bridge-Adapter fuer `student.create`

Priorität: Hoch

Beschreibung:

Der umgesetzte Adapter uebersetzt Dialogseiten- oder CLI-Eingaben fuer `student.create` in ein Application Command und uebergibt es an den Dispatcher.

Abgrenzung:

Keine Fachlogik im Adapter. Kein direkter Repository- oder SQLite-Zugriff aus CLI oder VBA.

Status:

Bis SQLite umgesetzt fuer `student.create`; Projection Refresh offen

### Python Bridge / CLI fuer SQLite-Schreibprozesse

Priorität: Hoch

Beschreibung:

Worksheet-basierte Dialogseiten uebergeben fuer `student.create` einen technischen Auftrag an Python. Python validiert und schreibt fachliche Daten in SQLite.

Abgrenzung:

Nicht Bestandteil von Sprint 5.2a.

Status:

Bis SQLite umgesetzt fuer `student.create`; weitere Schreibprozesse offen

### Command Queue fuer Dialogseiten-Schreibprozesse

Priorität: Hoch

Beschreibung:

Worksheet-basierte Dialogseiten sollen fachliche Schreibprozesse nicht direkt in Workbook-Tabellen ausfuehren, sondern einen technischen Auftrag fuer die Python-Service-Schicht erzeugen.

Abgrenzung:

Architekturspike vor produktiver Schueleranlage.

Status:

Durch Runtime Adapter und Projection Refresh Contract ersetzt

### Projection Refresh fuer geoeffnete Arbeitsmappe

Priorität: Hoch

Beschreibung:

Nach erfolgreichem Python Command erzeugt Python ein Projection-Refresh-Paket. VBA importiert ausschliesslich diesen Projection Output in registrierte Projektionsbereiche der geoeffneten Arbeitsmappe.

Abgrenzung:

Keine fachliche Logik in VBA. Kein direkter SQLite-Zugriff aus VBA. Keine durch VBA berechnete Projektion.

Status:

Architekturvertrag definiert; Implementierung offen

### Schüler anlegen

Priorität: Offen

Abgrenzung:

Produktive Schueleranlage ist nicht Bestandteil von Sprint 5.1a.

Status:

Implementierbar nach Runtime-Adapter-Vertrag

### Schüler bearbeiten

Priorität: Offen

Status:

Idee

### Schüler archivieren

Priorität: Offen

Beschreibung:

Schüler werden nicht physisch gelöscht.

Status:

Idee

## Epic: Stammgruppenverwaltung

### Stammgruppe anlegen

Priorität: Offen

Beschreibung:

Neue Stammgruppen werden über die Stammgruppenverwaltung angelegt, nicht automatisch beim Anlegen eines Schülers.

Status:

Idee

### Stammgruppe bearbeiten

Priorität: Offen

Status:

Idee

### Stammgruppe archivieren

Priorität: Offen

Status:

Idee

## Epic: Kursverwaltung

### Kurs anlegen

Priorität: Offen

Status:

Idee

### Kurs bearbeiten

Priorität: Offen

Status:

Idee

### Kurs archivieren

Priorität: Offen

Beschreibung:

Spätere Erweiterungen wie Farben und Jahrgänge bleiben möglich.

Status:

Idee

## Epic: Kursübersicht

### Schüler eines Kurses anzeigen

Priorität: Offen

Beschreibung:

Die Kursübersicht zeigt alle Schüler eines Kurses unabhängig von der Stammgruppe. Auf jeder Schülerkarte wird die Stammgruppe angezeigt.

Status:

Idee

### Kursverbünde löschen und Schüler-Umbuchung klären

Priorität: Offen

Beschreibung:

Kursverbuende werden persistent gespeichert. Offen bleiben Loeschen/Archivieren von Kursverbuenden und die fachliche Frage, ob beim Aendern von Stammgruppen oder Kursen spaeter Schueler-Umbuchungen angeboten werden sollen.

Status:

Folgethema

## Epic: Dashboard

Platzhalter für zukünftige Einträge.

## Epic: Berichte

Platzhalter für zukünftige Einträge.

## Epic: PySide Produktisierung

### Packaging / Installer fuer macOS

Priorität: Offen

Beschreibung:

Die PySide-Hauptanwendung braucht spaeter Packaging, Startpfad, Update-Strategie und macOS-taugliche Auslieferung.

Status:

Idee

### Produktiver SQLite-Datenbankpfad, Backup und Restore

Priorität: Offen

Beschreibung:

Der lokale SQLite-Pfad muss fuer echte Nutzung, Sicherung, Wiederherstellung und Updates definiert werden.

Status:

Idee

### SQLite-Persistenz ausbauen

Priorität: Offen

Beschreibung:

Beobachtungen, Kompetenzbewertungen, Medienreferenzen, Stammdaten und Kursverbuende muessen schrittweise ueber freigegebene Prozesse persistiert werden.

Status:

Idee

## Epic: Legacy und Export

### Legacy-Excel-Code pruefen und archivieren

Priorität: Offen

Beschreibung:

Workbook-Builder, Seeds und VBA-Quellen sollen spaeter gezielt geprueft, als Legacy markiert, archiviert oder entfernt werden, sobald sie fuer Export/Referenz nicht mehr gebraucht werden.

Status:

Idee

### Exportstrategie definieren

Priorität: Offen

Beschreibung:

Definieren, welche Excel-, PDF- oder Berichtsexporte aus SQLite erzeugt werden sollen und welche alten Workbook-Pfade dafuer erhalten bleiben.

Status:

Idee

### Alte Excel-/VBA-Build-Pfade entfernen

Priorität: Offen

Beschreibung:

Sobald Exportstrategie und Archivierung geklaert sind, koennen nicht mehr benoetigte Excel-/VBA-Pfade kontrolliert entfernt werden.

Status:

Idee

## Ideenparkplatz

Hier werden neue Ideen gesammelt, solange sie noch keinem Epic eindeutig zugeordnet werden können.
