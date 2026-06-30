# Architekturentscheidungen

## ADR-001

Excel-Dateien werden ausschließlich durch Python erzeugt.

Keine manuellen Änderungen.

## ADR-002

VBA ist ausschließlich für UI-Aufgaben freigegeben.

Keine fachliche Logik in VBA.

## ADR-003

Microsoft Excel für macOS ist die verbindliche Zielplattform.

## ADR-004

Die Projektentwicklung erfolgt sprintbasiert.

## ADR-005

Das Bewertungssystem besteht aus:

- `++`
- `+`
- `-`
- `--`

Die Darstellung erfolgt später über Ampelfarben.

## ADR-006

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs.

## ADR-007

Produktentscheidung.

Die Excel-Arbeitsmappe stellt die Benutzeroberfläche dar.

Die interne Datenstruktur darf technisch aufgebaut sein.

Die sichtbaren Arbeitsblätter orientieren sich ausschließlich an den Arbeitsabläufen der Lehrkraft.

## ADR-008

Produktentscheidung.

Die Stammgruppenübersicht bildet zukünftig eine zentrale Einstiegsansicht.

Bewertungen werden möglichst nur einmal erfasst.

Weitere Ansichten werden automatisch daraus erzeugt.

## ADR-009

Produktentscheidung.

Kompetenzen werden hierarchisch gespeichert.

Beispiel:

- Fach
- Lernbereich
- Kompetenzgruppe
- Kompetenz

## ADR-010

Produktentscheidung.

Das Datenmodell soll eine Entwicklungsdokumentation ermöglichen.

Mehrere Beobachtungen einer Kompetenz über einen längeren Zeitraum müssen zukünftig möglich sein.

## ADR-011

Produktentscheidung.

Die Software soll pädagogische Prozesse unterstützen.

Neue Funktionen werden danach bewertet, ob sie den Arbeitsalltag einer Lehrkraft vereinfachen.

## ADR-012 - Single Purpose Views

### Kontext

Während der Discovery-Phase und des UX-Entwurfs wurde festgestellt, dass Lehrkräfte je nach Situation unterschiedliche Ziele verfolgen:

- Im Unterricht soll möglichst schnell eine Beobachtung dokumentiert werden.
- Nach dem Unterricht soll die Kompetenzentwicklung analysiert werden.
- In der Stammgruppenübersicht soll lediglich ein Schüler ausgewählt werden.

Frühere Entwürfe versuchten, mehrere Aufgaben gleichzeitig auf einer Ansicht abzubilden.

Dadurch entstand unnötige Komplexität.

### Entscheidung

Jede Ansicht des Kompetenzmanagers verfolgt genau einen primären Zweck.

Jede zusätzliche Information oder Funktion wird daran gemessen, ob sie diesen Zweck unmittelbar unterstützt.

Neue Funktionen dürfen die Hauptaufgabe einer Ansicht nicht verwässern.

### Konsequenzen

Stammgruppenübersicht

- Primärer Zweck: Schüler schnell finden und auswählen.
- Keine Kompetenzbewertungen oder Analysen.
- Fokus auf schnelle Navigation.

Schülerprofil

- Primärer Zweck: Beobachtungen erfassen und Kompetenzentwicklung eines einzelnen Kindes verstehen.
- Einstieg über "Neue Beobachtung".

Kompetenzansicht

- Primärer Zweck: Entwicklung einer einzelnen Kompetenz nachvollziehen.

Schülerverwaltung

- Primärer Zweck: Schüler verwalten.
- Schüler hinzufügen, bearbeiten und archivieren.

Berichte

- Primärer Zweck: Vorbereitung pädagogischer Gespräche und Dokumentationen.

Dashboard

- Primärer Zweck: Handlungsbedarf sichtbar machen.

### Begründung

Dieses Prinzip reduziert die kognitive Belastung der Lehrkraft und sorgt dafür, dass jede Ansicht klar verständlich bleibt.

Neue Funktionen dürfen einer Ansicht nur hinzugefügt werden, wenn sie den primären Zweck dieser Ansicht unterstützen.

## ADR-013

Produktentscheidung.

Beobachtungen sind die fachliche Source of Truth.

Alle weiteren Informationen werden daraus abgeleitet.

## ADR-014

Produktentscheidung.

Eine Beobachtung kann mehreren Kompetenzen zugeordnet werden.

Begründung:

Eine Präsentation, Gruppenarbeit oder Lernzielkontrolle zeigt häufig mehrere Kompetenzen gleichzeitig.

Das Datenmodell muss diese Beziehung unterstützen.

## ADR-015

Produktentscheidung.

Kompetenzstände werden historisiert.

Frühere Entwicklungsstände werden nicht überschrieben.

Lernentwicklung soll nachvollziehbar bleiben.

## ADR-016

Produktentscheidung.

Die Benutzeroberfläche orientiert sich an den Arbeitsabläufen einer Lehrkraft.

Nicht an der internen Datenstruktur.

## ADR-017

Produktentscheidung.

Die Bewertungslogik bleibt zunächst:

- `++`
- `+`
- `-`
- `--`

Sie unterstützt den Alltag der Lehrkräfte.

Die eigentliche Lernentwicklung ergibt sich jedoch aus mehreren Beobachtungen über einen längeren Zeitraum.

## ADR-018

Produktentscheidung.

Die Software schlägt Kompetenzstände vor.

Die endgültige Festlegung erfolgt durch die Lehrkraft.

## ADR-019

Produktentscheidung.

Das Schülerprofil bildet den primären Arbeitsplatz.

Nicht Dashboard oder Stammgruppenmatrix.

## ADR-020

Produktentscheidung.

Die Benutzeroberfläche unterscheidet zwischen

- geplanten Beobachtungen
- spontanen Beobachtungen

## ADR-021 - UI-Technologie für UX-Prototypen ab v0.2

### Kontext

Der erste UX-Prototyp hat gezeigt, dass rein hyperlinkbasierte Arbeitsmappen für die nächste UX-Generation nicht ausreichen.

Die zweite Generation des UX-Prototyps wird auf Microsoft Excel für macOS ausgerichtet.

### Entscheidung

Python bleibt verantwortlich für:

- Workbook-Erzeugung
- Datenstruktur
- Styles
- Generierung
- Build-Artefakte

VBA übernimmt zukünftig ausschließlich:

- Navigation
- Dialoge
- Benutzerinteraktion
- UserForms

Fachliche Logik verbleibt vollständig im Python- und Datenmodell.

### Konsequenzen

VBA-Code darf keine fachlichen Regeln, Berechnungen, Kompetenzlogik oder Datenmodellentscheidungen enthalten.

Die Trennung zwischen Python-Generator, fachlichem Kern, UI-Screens und späteren VBA-Bausteinen wird vorbereitet, aber in Sprint 3.0 noch nicht groß refaktoriert.

Der bestehende Prototyp v0.1 bleibt als Referenz erhalten. Neue Arbeiten erfolgen ab v0.2.

## ADR-022 - Stammgruppenübersicht als Einstieg

### Kontext

Sprint 3.1 und Sprint 3.1a haben die damalige Klassenübersicht als erste Ansicht der zweiten UX-Prototyp-Generation konkretisiert. Ab Sprint 3.4 lautet die fachliche Bezeichnung `Stammgruppenübersicht`.

Das Review mit Product Owner und Jenaplan-Lehrkraft hat bestätigt, dass die Stammgruppenübersicht im Unterricht nur dann hilfreich ist, wenn sie schnell erfassbar bleibt und nicht zur Analyse- oder Verwaltungsansicht wird.

### Entscheidung

Die Stammgruppenübersicht ist ausschließlich der Einstieg in den Arbeitsablauf.

Ihre Aufgabe besteht darin:

- Schüler schnell zu finden
- Schüler auszuwählen
- anschließend in das Schülerprofil zu wechseln

Die Stammgruppenübersicht ist ausdrücklich:

- kein Dashboard
- keine Verwaltungsansicht
- keine Analyseansicht
- keine Auswertungsseite

### Konsequenzen

Die Stammgruppenübersicht enthält keine Kompetenzstände, Bewertungen, Analysen, Berichte, Statistiken oder Verwaltungsfunktionen.

Die gesamte Schülerkarte ist die spätere Klickfläche für den Wechsel ins Schülerprofil.

Ein separater Button innerhalb der Karte wird nicht verwendet.

## ADR-023 - Sortierung und Datenquelle der Stammgruppenübersicht

### Kontext

Lehrkräfte suchen Kinder im Unterricht überwiegend über den Vornamen.

Die Stammgruppenübersicht soll aus vorhandenen Schülerdaten entstehen und nicht manuell gepflegt werden.

### Entscheidung

Die Standardreihenfolge der Schüler in der Stammgruppenübersicht erfolgt alphabetisch nach Vorname.

Die Stammgruppenübersicht wird vollständig aus den vorhandenen Schülerdaten generiert.

Die technische Identität eines Schülers ist immer `student_id`.

Namen dienen nur Anzeige und Suche.

### Konsequenzen

Schülerkarten werden nicht manuell gepflegt.

Wenn Schüler in der Schülerverwaltung hinzugefügt, bearbeitet oder archiviert werden, aktualisiert sich die Stammgruppenübersicht automatisch aus diesen Daten.

Die Stammgruppenübersicht besitzt keine eigene Geschäftslogik.

Die verborgene Datenquelle der Stammgruppenübersicht ist eine abgeleitete UI-Projektion und darf keine eigene Schülerdaten-Quelle werden.

Alle Änderungen an Schülerdaten erfolgen über die Schülerverwaltung. Eine physische Löschung ist nicht vorgesehen.

## ADR-024 - Schülerverwaltung als separater Bereich

### Kontext

Die Stammgruppenübersicht soll im Unterricht schnelles Finden und Auswählen ermöglichen.

Verwaltungsfunktionen würden diesen Zweck verwässern.

### Entscheidung

Die Verwaltung von Schülern erfolgt künftig in einem separaten Bereich `Schülerverwaltung`.

Dort können Lehrkräfte:

- Schüler anlegen
- Schüler bearbeiten
- Schüler archivieren

### Konsequenzen

Die Stammgruppenübersicht enthält bewusst keine Verwaltungsfunktionen.

Die Schülerverwaltung ist der einzige UI-Ort für Änderungen an Schülerdaten. Schüler werden nicht physisch gelöscht, sondern archiviert.

## ADR-025 - Design Freeze Stammgruppenübersicht

### Kontext

Die Stammgruppenübersicht wurde unter der früheren Bezeichnung Klassenübersicht in Sprint 3.1 erstellt und in Sprint 3.1a auf Grundlage eines UX-Reviews für den Unterricht optimiert.

Laura hat das aktuelle Layout in Sprint 3.4 ausdrücklich freigegeben. Es gilt als Referenzdesign.

### Entscheidung

Die folgenden Eigenschaften der Stammgruppenübersicht dürfen in normalen Entwicklungssprints nicht verändert werden:

- Desktop-Anmutung
- Farbwelt
- Kartenlayout
- Kartenabstände
- Kartenhöhe
- Informationshierarchie
- Farbkonzept
- Typografie
- 4-spaltiges Raster
- Suchfeld
- Weißraum
- 140-%-Zoom der Stammgruppenübersicht
- kompakte Darstellung für Stammgruppen bis mindestens 28 Schüler

### Konsequenzen

Neue Ansichten orientieren sich am freigegebenen Referenzdesign.

Designänderungen erfolgen ausschließlich in einem eigenen UX-Sprint mit UX-Review und Product-Owner-Freigabe.

## ADR-026 - Schnellzugriff Neue Beobachtung

### Kontext

Im Unterricht soll eine Beobachtung schnell dokumentiert werden können.

Die Stammgruppenübersicht bleibt der Einstieg zum Finden und Auswählen eines Schülers.

Das Schülerprofil bleibt der vollständige Arbeitsbereich.

### Entscheidung

Eine Funktion besitzt genau eine Implementierung.

Eine Funktion darf jedoch mehrere Einstiegspunkte besitzen.

Die Funktion `Neue Beobachtung` kann künftig über die Stammgruppenübersicht und über das Schülerprofil gestartet werden.

Beide Einstiege öffnen denselben zentralen Beobachtungsdialog.

### Konsequenzen

Die Stammgruppenübersicht darf eine Kontextaktion `Neue Beobachtung` besitzen.

Diese Aktion arbeitet immer auf dem ausgewählten Schüler.

Die Stammgruppenübersicht startet keinen eigenen Beobachtungsprozess und enthält keine eigene Beobachtungslogik.

Sie übergibt ausschließlich `student_id` an den zentralen Beobachtungsdialog.

Der Beobachtungsdialog existiert projektweit nur einmal.

Das Datenmodell ändert sich dadurch nicht.

Alle Beobachtungen bleiben ausschließlich über `student_id` mit dem jeweiligen Schüler verknüpft.

## ADR-027 - Einführung von VBA als Interaktionsschicht

### Kontext

Die aktuelle UX-Prototyp-Generation wird als `.xlsx` durch Python erzeugt.

Diese Lösung funktioniert für statische Layouts, abgeleitete UI-Projektionen und einfache Formellogik.

Mit wachsender Interaktion entstehen jedoch technische Einschränkungen:

- Navigation ist an Zellpositionen gebunden.
- Hyperlinks können keine dynamische `student_id` übergeben.
- Dynamische Karten erschweren robuste Navigation.
- Der zentrale Dialog `Neue Beobachtung` ist ohne Interaktionsschicht nur mit Workarounds umsetzbar.
- Formeln und Hilfsspalten übernehmen zunehmend Aufgaben, die eigentlich UI-Interaktion sind.

### Variantenbewertung

#### Variante A: Python + `.xlsx` + Formeln

Stärken:

- Makrofrei.
- Einfach zu erzeugen.
- Geringere Sicherheitsbarrieren beim Öffnen.
- Gut geeignet für statische UI-Projektionen, Layouts und lesende Ansichten.

Schwächen:

- Navigation bleibt positionsgebunden.
- Keine robuste dynamische Übergabe von `student_id`.
- Dialoge und echte Benutzerinteraktion sind nur eingeschränkt möglich.
- Formeln werden schnell schwer wartbar.
- UX-Interaktion wandert in Hilfszellen und Schattentabellen.

#### Variante B: Python + `.xlsm` + VBA

Stärken:

- VBA kann `student_id` gezielt aus der UI-Projektion lesen und weitergeben.
- Navigation kann unabhängig von sichtbarer Kartenposition erfolgen.
- Ein zentraler Beobachtungsdialog kann projektweit einmal implementiert werden.
- UserForms und Ereignisse passen fachlich zur geplanten Excel/macOS-Desktop-Anwendung.
- Python kann weiterhin Workbook, Datenmodell, UI-Projektionen, Styles und Build-Artefakte erzeugen.

Schwächen und Risiken:

- `.xlsm` bringt Makro-Sicherheitsdialoge und organisatorische Freigaben mit sich.
- VBA-Entwicklung und Test auf macOS müssen explizit geprüft werden.
- Automatisches Erzeugen einer `.xlsm` mit VBA benötigt ein gültiges `vbaProject.bin` oder eine freigegebene Excel/VBA-Projekt-Injektion.
- Fachlogik darf nicht in VBA abwandern.

### Entscheidung

Für den Jenaplan-Kompetenzmanager wird VBA als Interaktionsschicht empfohlen.

Python bleibt verantwortlich für:

- Workbook-Erzeugung
- Datenmodell
- UI-Projektionen
- Styles
- Build-Artefakte

VBA übernimmt ausschließlich:

- Navigation
- Übergabe von `student_id`
- Dialogstart
- UserForms
- Benutzerinteraktion

Fachlogik, Datenmodellentscheidungen, Kompetenzlogik und Beobachtungsableitungen verbleiben vollständig im Python-/Datenmodell.

### Konsequenzen

Die Produktlinie sollte von `.xlsx` auf `.xlsm` erweitert werden, sobald der VBA-Spike technisch validiert ist.

Die bestehende `.xlsx`-Datei bleibt als Referenz- und Fallback-Artefakt erhalten.

Ein VBA-Proof-of-Concept muss vor einer breiten Umstellung zeigen:

- bestehendes Design bleibt unverändert,
- Zoom der Stammgruppenübersicht kann auf 140 % gesetzt werden,
- Klick auf eine sichtbare Schülerkarte funktioniert unabhängig von ihrer Position nach der Suche,
- `student_id` wird als einziger technischer Schlüssel übergeben,
- Schülerprofil öffnet sich,
- Zurück-Link funktioniert,
- keine Fachlogik entsteht in VBA.

### Spike-Ergebnis in dieser Umgebung

Microsoft Excel für macOS ist lokal installiert und per AppleScript erreichbar.

Ein vollständig automatisierter `.xlsm`-PoC konnte in dieser Umgebung noch nicht erzeugt werden, weil kein bestehendes `vbaProject.bin` vorhanden ist und die programmgesteuerte VBA-Projekt-Injektion nicht erfolgreich validiert werden konnte.

Der technische Packaging-Spike bestätigt die Hürde:

- Im Repository existiert aktuell kein `vbaProject.bin`, keine `.xlsm`-Vorlage und kein exportiertes VBA-Projekt.
- Die bestehende `Jenaplan_UX_Prototype_v0.2.xlsx` enthält kein `xl/vbaProject.bin`, keine VBA-Relationship und keinen macro-enabled Content-Type.
- `openpyxl` kann ein vorhandenes VBA-Projekt beim Laden mit `keep_vba=True` erhalten und beim Speichern wieder in eine `.xlsm` übernehmen.
- `openpyxl` kann kein neues VBA-Projekt erzeugen und keine `.bas`-, `.cls`- oder UserForm-Quellen zu einem gültigen `vbaProject.bin` kompilieren.
- Eine bloß umbenannte oder leere `.xlsm` ohne eingebettetes VBA-Projekt gilt nicht als valider PoC.

Für einen reproduzierbaren `.xlsm`-Build ist daher ein einmalig erzeugter und validierter VBA-Seed erforderlich.

Der bevorzugte Build-Prozess ist:

1. VBA-Quellen zusätzlich lesbar im Repository pflegen, zum Beispiel unter `vba/`.
2. Das VBA-Projekt einmalig in Microsoft Excel für macOS in einer Macro-enabled-Arbeitsmappe erstellen und testen.
3. Das daraus entstehende `vbaProject.bin` oder eine minimale `.xlsm`-Seed-Datei als Build-Artefakt versionieren.
4. Python erzeugt weiterhin Workbook, Datenmodell, UI-Projektionen und Styles.
5. Der Packaging-Schritt lädt den Seed mit `keep_vba=True` oder übernimmt das vorhandene `vbaProject.bin` in die generierte Arbeitsmappe.
6. Die erzeugte `.xlsm` wird technisch geprüft: `xl/vbaProject.bin`, macro-enabled Content-Type, VBA-Relationship und Smoke-Test in Excel für macOS.

Bis dieser Seed existiert, bleibt die `.xlsx`-Datei das verlässliche Build-Artefakt. Die `.xlsm`-Linie wird erst eingeführt, wenn der Packaging-Prozess mit echtem VBA-Projekt validiert ist.

## ADR-028 - Konsolidierte Zielarchitektur und Entwicklungsreihenfolge

### Kontext

Die UX-Prototyp-Generation ab v0.2 richtet sich vollständig auf Microsoft Excel für macOS aus.

Die Architekturarbeit zu VBA hat bestätigt, dass Interaktion, Dialoge und UserForms langfristig nicht sauber über reine `.xlsx`-Formeln abgebildet werden können.

Gleichzeitig bleibt das Datenmodell die fachliche Grundlage des Produkts.

### Entscheidung

Microsoft Excel für macOS ist die verbindliche Zielplattform.

Python bleibt verantwortlich für:

- Build-System
- Workbook-Erzeugung
- Datenmodell
- UI-Projektionen
- Styles
- Berichte
- Fachlogik

VBA übernimmt nach erfolgreichem Packaging ausschließlich:

- Navigation
- Buttons
- Dialoge
- UserForms
- Benutzerinteraktion

Keine Fachlogik wird in VBA implementiert.

Das Datenmodell bleibt vollständig unabhängig von VBA.

### Datenmodell-Prinzip

Das Datenmodell ist die fachliche Grundlage des Projekts.

Neue UI-Elemente, Formeln, Hilfstabellen, VBA-Routinen und Screens dürfen das Datenmodell niemals umgehen.

Alle Ansichten sind Projektionen des Datenmodells.

### Entwicklungsreihenfolge

Jede Implementierung folgt künftig dieser Reihenfolge:

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

### Konsequenzen

Bis ein validierter VBA-Seed existiert, bleibt `.xlsx` das produktive Build-Artefakt.

Nach erfolgreichem Packaging kann die `.xlsm`-Linie als Interaktionsschicht eingeführt werden, ohne Python, Datenmodell oder Fachlogik zu ersetzen.

### Validierung

Sprint 3.3b hat praktisch bestätigt, dass Microsoft Excel für macOS, Python und VBA technisch zusammenarbeiten:

- Ein manuell in Excel erzeugter `.xlsm`-Seed wurde mit `openpyxl` und `keep_vba=True` geladen.
- Python konnte die Arbeitsmappe verändern und wieder als `.xlsm` speichern.
- Das eingebettete `xl/vbaProject.bin` blieb erhalten.
- Das Makro lief anschließend in Microsoft Excel für macOS.

Sprint 3.3c bereitet die `.xlsm`-Linie als Zielartefakt vor. `.xlsx` bleibt Fallback, bis das VBA-Framework stabil ist.

Die lesbaren VBA-Quellen liegen unter `vba/modules/`. Sie ersetzen nicht das binäre `vbaProject.bin`; für ausführbaren VBA-Code muss der Seed nach Import der Module in Excel aktualisiert werden.

Die Bereinigung von VBA-Projektobjekten wie Workbook- und Worksheet-CodeNames erfolgt im Zweifel manuell im VBA-Editor. Python darf das binäre `vbaProject.bin` erhalten und strukturell prüfen, aber nicht durch nicht validierte Binärmanipulationen verändern.

## ADR-029 - Design-System als Source of Truth

### Kontext

Laura hat den aktuellen UX-Prototypen begutachtet und das Design der Stammgruppenübersicht ausdrücklich freigegeben.

Das freigegebene Design soll künftig nicht in normalen Entwicklungssprints verändert werden.

### Entscheidung

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.

Das freigegebene Referenzdesign umfasst insbesondere:

- Farbwelt
- Typografie
- Kartenlayout
- Kartenabstände
- Desktop-App-Anmutung
- 140-%-Zoom der Stammgruppenübersicht
- Suchfeld
- Weißraum
- visuelle Hierarchie

Neue Ansichten müssen sich daran orientieren.

Designänderungen dürfen künftig ausschließlich über einen eigenen UX-Sprint erfolgen.

### Konsequenzen

Normale Entwicklungssprints verändern das Design nicht.

Die Dokumentation des Design-Systems liegt in `docs/DESIGN_SYSTEM.md`.

Python erzeugt weiterhin die Benutzeroberflächen aus dem freigegebenen Design-System.

## ADR-030 - Stammgruppe und Kurs als eigenständige Domänenentitäten

### Kontext

Laura hat das fachliche Modell präzisiert.

Die bisher verwendete Bezeichnung `Klasse` ist fachlich nicht genau genug.

### Entscheidung

Die Domänensprache ersetzt `Klasse` vollständig durch `Stammgruppe`.

Jeder Schüler gehört genau einer Stammgruppe an.

Jeder Schüler gehört zusätzlich genau einem Kurs an.

Der Kurs beschreibt den Jahrgang.

Die Stammgruppe beschreibt die organisatorische Zugehörigkeit.

Stammgruppe und Kurs sind eigenständige fachliche Entitäten.

### Datenmodell-Konsequenzen

Student enthält:

- `student_id`
- Vorname
- Nachname
- `stammgruppe_id`
- `kurs_id`

Stammgruppe enthält:

- `stammgruppe_id`
- Name

Kurs enthält:

- `kurs_id`
- Name
- optionale Farbe für spätere UI

Die `student_id` bleibt technische Identität.

Das Datenmodell bleibt Source of Truth.

### UI-Konsequenzen

Die bisherige Klassenübersicht heißt künftig `Stammgruppenübersicht`.

Die Stammgruppenübersicht zeigt Schüler einer Stammgruppe. Die Kartenfarbe orientiert sich künftig am Kurs. Die Suche bleibt unverändert.

Zusätzlich wird eine neue Hauptansicht `Kursübersicht` aufgenommen.

Die Kursübersicht zeigt alle Schüler eines Kurses unabhängig von der Stammgruppe. Auf jeder Schülerkarte wird die Stammgruppe angezeigt.

Beide Ansichten greifen auf dieselben Schülerdaten zu. Es existieren keine doppelten Daten.

Die Ansichten sind ausschließlich Projektionen des Datenmodells.

### Verwaltungsfunktionen

Die Schülerverwaltung umfasst:

- Schüler anlegen
- Schüler bearbeiten
- Schüler archivieren

Schüler werden nicht physisch gelöscht.

Die Stammgruppenverwaltung umfasst:

- Stammgruppe anlegen
- Stammgruppe bearbeiten
- Stammgruppe archivieren

Neue Stammgruppen werden über die Stammgruppenverwaltung angelegt, nicht automatisch beim Anlegen eines Schülers.

Die Kursverwaltung umfasst:

- Kurs anlegen
- Kurs bearbeiten
- Kurs archivieren

Spätere Erweiterungen wie Farben und Jahrgänge bleiben möglich.

## ADR-031 - Dokumentation geht Implementierung voraus

### Kontext

Sprint 4 legt die Core Data Architecture als verbindliche Grundlage fuer spaetere Produktfunktionen fest.

Ohne dokumentierte Datenquellen, technische Namen, View Ownership und Data Lifecycles wuerden spaetere Sprints erneut lokale technische Entscheidungen treffen.

### Entscheidung

Dokumentation geht Implementierung voraus.

Neue Funktionen werden kuenftig erst nach der Architekturpruefung und Registry-Erweiterung umgesetzt.

Die verbindliche Reihenfolge lautet:

1. `PROJECT_CONSTITUTION.md` pruefen
2. `TECHNICAL_NAMES.md` pruefen
3. `DATA_REGISTRY.md` erweitern
4. `DATA_LIFECYCLE.md` ergaenzen
5. `VIEW_DATA_OWNERSHIP.md` ergaenzen
6. `UI_DATA_MAPPING.md` ergaenzen
7. erst danach Implementierung

### Begruendung

Die Architektur soll zukuenftige Implementierungen vereinfachen und Inkonsistenzen verhindern.

Funktionen sollen datengetrieben entstehen und keine eigenen Schattenmodelle, lokalen Zwischendaten oder kreativen technischen Namen einfuehren.

### Konsequenzen

Keine neue Datenquelle ohne `DATA_REGISTRY.md`.

Keine neue technische Bezeichnung ohne `TECHNICAL_NAMES.md`.

Keine neue Ansicht ohne `VIEW_DATA_OWNERSHIP.md`.

Keine neue UI-Komponente ohne `UI_DATA_MAPPING.md`.

Kein Schreibprozess ohne `DATA_LIFECYCLE.md`.

Feature-Sprints duerfen bestehende Legacy-Namen nicht spontan umbenennen.

## ADR-032 - Entity-first-Architektur

### Kontext

Ab Sprint 4 soll die erste produktnahe Umsetzung auf einer stabilen Datenarchitektur aufsetzen.

Wenn neue Funktionen zuerst als Masken gedacht werden, entstehen leicht lokale Datenhaltung, Schattenlogik und technische Namen ausserhalb der Registry.

### Entscheidung

Funktionen werden von Entitaeten und Datenfluessen aus gedacht, nicht von Masken.

Die verbindliche Reihenfolge lautet:

```text
Entity
-> Storage
-> Builder
-> UI-Projektion
-> VBA-Navigation
```

### Konsequenzen

Neue Verwaltungsfunktionen beginnen mit der Frage, welche Entitaet entsteht oder erweitert wird.

UI wird erst nach Entity, Storage und Builder-Projektion entworfen.

## ADR-033 - Builder als eigene Architekturschicht

### Kontext

Python erzeugt Workbook, Datenquellen, Styles und UI-Projektionen.

Diese Verantwortung muss als eigene Schicht sichtbar bleiben, damit Datenmodell und Excel-UI nicht vermischt werden.

### Entscheidung

Der Builder ist die verbindliche Schicht zwischen Daten und Workbook/UI.

```text
Data
-> Builder
-> Workbook/UI
-> VBA-Interaktion
```

Der Builder erzeugt Hidden Data Sheets, Excel-Tabellen, Named Ranges, UI-Projektionen und vorbereitete Navigationspunkte.

### Konsequenzen

Der Builder enthaelt keine spontane Fachlogik ausserhalb der Data Registry.

VBA greift nicht direkt auf fachliche Tabellen zu.

UI-Projektionen werden aus registrierten Datenquellen erzeugt.

## ADR-034 - Historisierung von Bezeichnern bleibt offene Entscheidung

### Kontext

Kurse, Stammgruppen und Kompetenzen koennen spaeter umbenannt werden.

Beobachtungen und Berichte koennen historische Kontexte anzeigen.

### Entscheidung

Noch nicht final entschieden ist, ob historische Beobachtungen bei geaenderten Kompetenznamen, Kursnamen oder Stammgruppennamen den aktuellen Namen oder den damals gueltigen Namen anzeigen.

Diese Entscheidung muss vor produktiver Beobachtungserfassung getroffen werden.

### Offene Frage

Wenn Kompetenznamen, Kursnamen oder Stammgruppennamen spaeter geaendert werden, zeigen historische Beobachtungen dann den aktuellen Namen oder den damals gueltigen Namen?

### Konsequenzen

Sprint 4.1 darf keine produktive Beobachtungserfassung einfuehren, ohne diese Frage vorher zu klaeren.

Schueler-, Kurs- und Stammgruppenverwaltung muessen stabile IDs erhalten, unabhaengig von sichtbaren Namen.

## ADR-035 - Modale UserForms und studentenzentrierte Dokumentreferenzen

### Kontext

Sprint 5 bereitet die erste echte Eingabemaske des Kompetenzmanagers vor.

Der Kompetenzmanager soll als Anwendung verstanden werden.

Excel ist die Runtime, nicht der Ort fuer direkte fachliche Eingaben in Tabellen.

Gleichzeitig sollen Dokumente und Medien spaeter angebunden werden, ohne Excel-Dateien durch eingebettete Anlagen zu belasten.

### Entscheidung

Fachliche Eingaben erfolgen ueber modale VBA-UserForms.

UserForms sammeln Eingaben, fuehren nur einfache Oberflaechenvalidierung durch und rufen freigegebene Services auf.

UserForms enthalten keine Businesslogik und schreiben nicht direkt in fachliche Workbook-Tabellen.

Die erste Referenz-UserForm ist `frm_student_new` fuer den Zielzustand `Neuer Schueler`.

Dateien werden nicht in Excel eingebettet.

Dokumente und Medien werden studentenzentriert im Dateisystem abgelegt.

Excel speichert nur Referenzen und Metadaten in `data_media`.

Beobachtungsanhaenge liegen ebenfalls unter dem Schueler und tragen zusaetzlich den Bezug zur Beobachtung.

### Konsequenzen

`data_media` wird als bestehende Datenquelle fuer Dokument- und Medienreferenzen vorbereitet.

Der Schuelerbezug `student_id` wird fuer Dokumente und Medien verbindlich.

Ein Beobachtungsanhang besitzt zusaetzlich `observation_id`.

Der Beobachtungsdialog wird nur vorbereitet und nicht in Sprint 5 implementiert.

Kompetenzen muessen im Beobachtungsdialog zwingend mitgedacht werden.

Schnellbeobachtung und Gruppenbewertung bleiben Backlog-Themen.
