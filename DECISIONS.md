# Architekturentscheidungen

## ADR-001

Excel-Dateien werden ausschließlich durch Python erzeugt.

Keine manuellen Änderungen.

## ADR-002

VBA ist ausschließlich für UI-Aufgaben freigegeben.

Keine fachliche Logik in VBA.

## ADR-003

Historische Entscheidung: Microsoft Excel für macOS war die verbindliche Zielplattform.

Fuer die Hauptanwendung wird diese Entscheidung durch ADR-045 abgeloest. Excel bleibt Export-, Berichts- oder Legacy-Projektion.

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

Die Stammgruppenübersicht enthält bewusst keine Verwaltungslogik.

Ein freigegebener Navigationsabsprung zu einer separaten Schuelerverwaltungs- oder Dialogseite ist zulaessig, solange die Stammgruppenübersicht selbst keine Schuelerdaten bearbeitet, validiert oder speichert.

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

Historische Entscheidung: Microsoft Excel für macOS war die verbindliche Zielplattform fuer die damalige UX-Prototyp-Generation.

Fuer die Hauptanwendung wird diese Entscheidung durch ADR-045 abgeloest.

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

## ADR-036 - Sprint 5.1b stoppt an fehlender VBA-zu-Python-Service-Bruecke

### Kontext

Sprint 5.1b sollte `frm_student_new` erstmals produktiv an die Schueleranlage anbinden.

Der vorgesehene Ablauf war:

```text
UserForm
-> StudentService.create_student()
-> StudentRepository
-> tbl_students
-> aktualisierte Stammgruppenuebersicht
```

Die UserForm darf dabei keine Businesslogik enthalten und niemals direkt in `tbl_students` schreiben.

### Befund

`StudentService` ist aktuell eine Python-Laufzeitkomponente.

Die produktive UserForm laeuft in Excel/VBA.

Im Projekt existiert noch kein freigegebener, validierter Mechanismus, mit dem VBA auf macOS den Python-`StudentService` direkt, reproduzierbar und releasefaehig aufrufen kann.

Eine direkte Tabellenlogik in VBA waere ein Architekturbruch, weil dadurch die freigegebene Service-/Repository-Schicht umgangen wuerde.

### Entscheidung

Sprint 5.1b wird an dieser Stelle technisch gestoppt.

Historischer Stand: `frm_student_new` wurde nicht produktiv angebunden, solange keine freigegebene Bruecke zwischen VBA-UserForm und fachlicher Python-Schicht entschieden war.

Dieser Stopp bezog sich auf die inzwischen verworfene primaere VBA-UserForm-Strategie. Fuer worksheet-basierte Dialogseiten definiert ADR-043 den Runtime Adapter und den Refresh Contract.

Es wird kein Workaround umgesetzt, der in VBA direkt in fachliche Tabellen schreibt.

### Technische Optionen

Python Build/Import Workflow:

- Eingaben werden nicht live aus VBA verarbeitet.
- Python bleibt alleiniger Schreiber der Workbook-Datenquellen.
- Vorteil: passt zur bestehenden Architektur.
- Nachteil: kein echter Live-Dialog in der geoeffneten Excel-Datei.

VBA Repository-Schicht:

- VBA erhaelt eine eigene, eng begrenzte Repository-Schicht fuer freigegebene Schreibprozesse.
- Vorteil: echter Live-Dialog in Excel moeglich.
- Nachteil: fachliche Regeln muessen streng aus VBA herausgehalten und gegen Python-Regeln abgesichert werden.

CSV/Hidden-Sheet Command Queue:

- VBA schreibt nur einen technischen Befehl in eine Queue; Python verarbeitet ihn spaeter ueber Services.
- Vorteil: UserForm bleibt duenn und Service-Logik bleibt in Python.
- Nachteil: benoetigt einen klaren Synchronisations- und Aktualisierungsprozess.

SQLite/API:

- Excel/VBA spricht mit einer externen Daten- oder Service-Schicht.
- Vorteil: sauberer Anwendungsschnitt.
- Nachteil: groesserer Technologiesprung und zusaetzlicher Betrieb.

### Empfehlung

Empfohlen wird als naechster Architekturspike die Command-Queue-Variante.

Sie haelt die UserForm duenn, vermeidet direkte VBA-Tabellenschreiblogik und laesst `StudentService` weiterhin die fachliche Schueleranlage koordinieren.

Vor produktiver Schueleranlage muss entschieden werden:

- wo die Command Queue liegt
- wann Python sie verarbeitet
- wie die Stammgruppenuebersicht danach aktualisiert wird
- wie Fehler aus `StudentValidator` wieder in den Dialog oder an die Nutzerin gemeldet werden

### Konsequenzen

Sprint 5.1b fuehrt keine produktive Schueleranlage ein.

`OpenNewStudentDialog()` und `frm_student_new` bleiben vorbereitet, aber ohne produktiven Schreibpfad.

Der naechste Schritt ist eine Architekturentscheidung zur Laufzeitbruecke zwischen Excel/VBA und Python-Service-Schicht.

## ADR-037 - SQLite als moegliche zentrale Datenbasis geprueft

### Kontext

Sprint 5.2a prueft SQLite als technische Grundlage fuer spaetere UserForm-Schreibprozesse.

Der Zielpfad lautet:

```text
VBA UserForm
-> Python Bridge / CLI
-> SQLite DB
-> Python Builder
-> Excel-Projektion
```

VBA darf dabei nicht direkt in SQLite schreiben.

Python bleibt die fachliche Schreibschicht.

### Entscheidung

SQLite wird als moegliche neue Source of Truth weiterverfolgt.

Der Spike erzeugt eine SQLite-Datenbank unter `data/kompetenzmanager.sqlite`.

Der urspruenglich vorgeschlagene Pfad `Daten/kompetenzmanager.sqlite` wird nicht eingefuehrt, weil das Projekt bereits die Konvention `data/` fuer Datenartefakte verwendet.

Im Spike werden nur die bestehenden Entitaeten Student, Group und Course abgebildet:

- `students`
- `groups`
- `courses`

Die bestehenden IDs bleiben unveraendert:

- `STU-000001` usw.
- `GRP-000001` usw.
- `CRS-000001` usw.

### Befund

Python kann die SQLite-Datenbank erzeugen.

Python kann Seed-Daten fuer Students, Groups und Courses in SQLite schreiben.

Python kann diese Daten ueber SQLite-Repositories lesen.

Der bestehende Builder kann aus den SQLite-gelesenen Daten die bisherige Excel-Projektion erzeugen.

Die Excel-Projektion bleibt dabei weiterhin eine Projektion und wird nicht zur fachlichen Source of Truth.

### Konsequenzen

SQLite ist noch nicht produktive Source of Truth.

Die Workbook-Tabellen `tbl_students`, `tbl_groups` und `tbl_courses` bleiben im Spike Projektions- und Kompatibilitaetsschicht fuer Excel.

Wenn SQLite produktiv eingefuehrt wird, muss es genau eine fachliche Source of Truth geben:

- entweder SQLite als Storage und Excel als Projektion
- oder der aktuelle Workbook-Storage

Ein paralleler Schreibbetrieb in SQLite und Workbook-Tabellen ist nicht erlaubt.

### Risiken

- Historischer Stand: Python Bridge / CLI fuer UserForms war zu diesem Zeitpunkt noch nicht entschieden. Fuer worksheet-basierte Dialogseiten definiert ADR-043 den Runtime Adapter und den Refresh Contract.
- Fehler aus Python-Validierung muessen spaeter kontrolliert an Excel/VBA zurueckgemeldet werden.
- Dateiablage, Backup, Sperren und Mehrfachzugriff der SQLite-Datei sind noch nicht geklaert.
- Vollstaendige Migration weiterer Entitaeten, insbesondere Beobachtungen, Kompetenzen und Dokumentreferenzen, ist nicht Teil dieses Spikes.
- Der produktive Buildpfad darf erst umgestellt werden, wenn SQLite als Source of Truth final freigegeben ist.

### Empfehlung

SQLite soll als Zielarchitektur fuer die fachliche Datenhaltung weiter geprueft werden.

Der naechste sinnvolle Sprint ist ein Python-Bridge-/CLI-Spike:

- UserForm erzeugt keinen direkten Datenbankzugriff.
- VBA startet oder uebergibt spaeter nur einen technischen Auftrag.
- Python verarbeitet den Auftrag, nutzt Services und Repositories und aktualisiert SQLite.
- Der Builder erzeugt danach die Excel-Projektion aus SQLite.

## ADR-038 - Application Command Layer zwischen Adaptern und Domain Services

### Kontext

Nach dem SQLite-Spike braucht der Kompetenzmanager eine technische Bruecke zwischen Excel/VBA und der Python-Domaene.

Eine CLI ist dafuer nur ein moeglicher Adapter.

Die fachliche Steuerung darf nicht in CLI, VBA oder Excel-Logik wandern.

### Entscheidung

Zwischen Command-Adaptern und Domain Services wird ein Application Command Layer eingefuehrt.

Zielarchitektur:

```text
VBA
-> Command Adapter
-> Application Command Dispatcher
-> Domain Services
-> Repositories
-> SQLite
-> Builder
-> Excel-Projektion
```

Python bleibt die einzige fachliche Schreibschicht.

VBA enthaelt keine Businesslogik.

SQLite bleibt Zielarchitektur fuer fachliche Datenhaltung.

Excel bleibt Projektions- und UI-Schicht.

### Struktur

Empfohlene Struktur:

```text
src/application/
|-- dispatcher.py
`-- commands/
    |-- student.py
    |-- observation.py
    `-- report.py
```

`dispatcher.py` enthaelt den Application Command Dispatcher.

`commands/` enthaelt reine Command-DTOs, zum Beispiel `CreateStudentCommand` fuer `student.create`.

### Dispatcher-Design

Der Dispatcher nimmt ein Command mit `command_name` entgegen.

Er kennt keine Fachlogik.

Er leitet das Command an einen registrierten Handler weiter.

Der Handler ist die Verbindung zum passenden Domain Service, zum Beispiel:

```text
student.create
-> StudentService.create_student()
```

Der Dispatcher erzeugt keine IDs selbst, validiert keine Fachregeln und schreibt nicht in SQLite.

### CLI-Design

Eine spaetere CLI, zum Beispiel `python3 km.py student create`, ist nur ein Adapter.

Die CLI darf:

- Argumente entgegennehmen
- daraus ein Command-DTO bauen
- das Command an den Dispatcher uebergeben
- technische Fehlercodes und Meldungen zurueckgeben

Die CLI darf nicht:

- fachliche Regeln enthalten
- direkt Repositories aufrufen
- direkt in SQLite schreiben
- Excel-Projektionen selbst veraendern

### VBA-Anbindung

VBA ruft spaeter keinen Domain Service direkt auf.

VBA sammelt UI-Eingaben und uebergibt sie an einen Command Adapter.

Der Adapter uebergibt ein Command an den Dispatcher.

VBA bleibt Interaktionsschicht und enthaelt keine Businesslogik.

### Konsequenzen

Sprint 5.3 fuehrt keine produktive CLI und keine UserForm-Anbindung ein.

Der Application Layer ist ein Architektur-Skelett und noch keine vollstaendige Command-Menge.

Der naechste sinnvolle Sprint prueft einen konkreten Adapter fuer `student.create`, bevorzugt als CLI-/Python-Bridge-Spike.

## ADR-039 - student.create durchlaeuft den Python-Application-Stack

### Kontext

Sprint 5.4 prueft `student.create` ohne CLI, ohne VBA und ohne Excel.

Nachgewiesen werden soll nur der Python-Stack:

```text
ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService.create_student()
-> SQLiteStudentRepository
-> SQLite
```

### Entscheidung

`student.create` wird als erster End-to-End-Command im Python-Stack akzeptiert.

Der Dispatcher enthaelt keine Fachlogik und kein SQL.

Der Dispatcher liefert ein `SuccessResult`, wenn der Handler erfolgreich durchlaeuft.

Der Dispatcher liefert ein `ErrorResult`, wenn Domain- oder Repository-Fehler entstehen.

`StudentService` bleibt fuer fachliche Validierung, ID-Erzeugung und Prozesskoordination verantwortlich.

`SQLiteStudentRepository` ist fuer den Schreibzugriff auf SQLite verantwortlich.

### Konsequenzen

SQLite kann im Python-Stack als Source of Truth fuer `student.create` verwendet werden.

Adapter fehlen weiterhin:

- keine CLI
- keine VBA-Anbindung
- kein Prozessstart aus Excel
- keine Rueckmeldung an eine UserForm

Der naechste Sprint kann den ersten Adapter fuer `student.create` pruefen, ohne die fachliche Logik aus dem Python-Stack herauszuziehen.

Offen bleiben:

- Prozessstart aus Excel/VBA auf macOS
- Fehler-Rueckmeldung vom Python-Prozess an VBA
- Transaktionsgrenzen bei SQLite-Schreibprozessen
- anschliessender Rebuild oder Refresh der Excel-Projektion

## ADR-040 - Architecture Baseline v2.0

Status: Accepted

### Motivation

Die urspruengliche Excel-zentrierte Loesung war als schneller UX- und Workbook-Prototyp richtig.

Mit wachsendem Funktionsumfang reicht eine reine Workbook-Architektur aber nicht mehr aus:

- fachliche Schreibprozesse wie Schueleranlage, Beobachtungserfassung und Dokumentreferenzen brauchen stabile Transaktionen
- VBA darf keine Businesslogik enthalten
- Excel darf keine fachlichen Datenentscheidungen treffen
- fachliche Daten duerfen nicht gleichzeitig in UI-Projektionen und Tabellenlogik entstehen
- spaetere UserForms brauchen einen sauberen Weg in die Python-Domaene

Die Architektur wurde deshalb kontrolliert erweitert, ohne die bisherigen Erkenntnisse zu verlieren: Excel bleibt Zieloberflaeche und Projektion, Python bleibt fachliche Schicht, SQLite wird als zentrale Datenbasis vorbereitet.

### Architecture v1

Die erste tragfaehige Architektur war:

```text
Python
-> Workbook Builder
-> Excel
```

Python erzeugte Workbook-Struktur, Datenblaetter, UI-Projektionen und Styles.

Excel war Zielartefakt und sichtbare Arbeitsoberflaeche.

Diese Architektur bleibt historisch wichtig, weil sie die datengetriebene Projektion, strukturierte Tabellen, stabile IDs und reproduzierbare Builds eingefuehrt hat.

### Architecture Baseline v2.0

Die aktuell validierte Baseline lautet:

```text
                    Adapter Layer
           (VBA / CLI / zukuenftige Adapter)

                         |

               Application Layer
              (Dispatcher / Commands)

                         |

                  Domain Layer
             (Services / Validatoren)

                         |

              Infrastructure Layer
              (SQLite / Repository)

                         |

               Projection Layer
               (Workbook Builder)

                         |

                    Excel UI
```

### Verantwortlichkeiten

Adapter Layer:

- nimmt Benutzerinteraktionen oder technische Aufrufe entgegen
- baut Commands fuer die Application-Schicht
- enthaelt keine Fachlogik
- schreibt nicht direkt in SQLite

Application Layer:

- definiert Commands
- routet Commands ueber den Dispatcher
- erzeugt `SuccessResult` oder `ErrorResult`
- enthaelt keine Businesslogik, kein SQL und keine Excel-Logik

Domain Layer:

- enthaelt die fachliche Logik
- validiert Eingaben ueber Validatoren
- koordiniert fachliche Prozesse ueber Services
- erzeugt fachliche IDs nach freigegebener Strategie

Infrastructure Layer:

- kapselt Persistenz
- enthaelt Repositories
- liest und schreibt SQLite
- ist die einzige Schicht mit direktem Datenbankzugriff

Projection Layer:

- erzeugt Workbook-Datenblaetter, strukturierte Tabellen, Named Ranges und UI-Projektionen
- liest aus registrierten Datenquellen
- enthaelt keine Fachlogik

Excel UI:

- zeigt Projektionen
- ermoeglicht Navigation und Interaktion
- trifft keine fachlichen Datenentscheidungen
- ist nicht Source of Truth

### Architekturprinzipien

- SQLite ist die vorbereitete Source of Truth fuer fachliche Daten.
- Python ist die einzige fachliche Schreibschicht.
- Excel enthaelt keine fachlichen Datenentscheidungen.
- VBA enthaelt keine Businesslogik.
- Repositories kapseln Persistenz.
- Builder erzeugen ausschliesslich Projektionen.
- Commands bilden den Einstiegspunkt fachlicher Ablaeufe.
- Adapter sind austauschbar und duerfen keine Fachlogik enthalten.
- Es gibt keine parallele fachliche Schreibquelle neben SQLite.

### Standard-Datenfluss

Der Standardablauf fuer zukuenftige Schreibprozesse ist:

```text
User
-> worksheet-basierte Dialogseite oder freigegebener Adapter
-> Adapter
-> Dispatcher
-> Command
-> Service
-> Repository
-> SQLite
-> Builder
-> Excel-Projektion
```

### Auswirkungen

Alle zukuenftigen Module folgen dieser Baseline.

Das gilt insbesondere fuer:

- Schueler
- Beobachtungen
- Kompetenzen
- Dokumente
- Berichte

Sonderarchitekturen sind nicht zulaessig.

Neue Module muessen entweder in diese Schichten eingeordnet werden oder vorab eine explizite Architekturentscheidung erhalten.

### Abgrenzung

Diese Baseline fuehrt keine neue Implementierung ein.

Sie dokumentiert den bereits validierten Stand aus:

- SQLite Architecture Spike
- Application Command Layer
- `student.create` End-to-End durch den Python-Stack

Historischer Stand bei Annahme der Baseline: Offen blieben Adapter, produktive CLI, VBA-Prozessstart, UserForm-Anbindung und automatischer Refresh der Excel-Projektion. ADR-043 klaert Runtime Adapter und Refresh Contract fuer `student.create`; die konkrete Implementierung bleibt offen.

## ADR-041 - UX-Prototyp als verbindlicher Schritt vor UserForm-Umsetzung

Status: Superseded by ADR-042

### Kontext

Feature 1 `Neuer Schueler` soll als erste produktive UserForm des Kompetenzmanagers entstehen.

Die UserForm ist Teil des Adapter Layers und darf keine Fachlogik, keine direkte Tabellenlogik und keine SQLite-Kommunikation enthalten.

Gleichzeitig muss das visuelle Verhalten vor der technischen Umsetzung mit Laura bzw. dem Product Owner abgestimmt werden.

### Entscheidung

Fuer neue UserForms wird ein UX-Prototyp als verbindlicher Zwischenschritt eingefuehrt.

Der Ablauf lautet:

1. UX-Prototyp erstellen
2. UX-Review mit Laura bzw. Product Owner durchfuehren
3. UX-Freigabe dokumentieren
4. VBA-UserForm moeglichst 1:1 nach dem freigegebenen UX-Prototyp umsetzen
5. Validierung, Adapter-Anbindung und fachliche Logik erst danach ergaenzen

Der UX-Prototyp ist keine technische Implementierung.

Er ist die visuelle Referenz fuer die spaetere UserForm.

Designentscheidungen fuer UserForms werden im UX-Prototyp getroffen, nicht frei im VBA-Designer.

### Feature-1-Stand

Die Datei `output/Jenaplan_UX_Prototype_v0.1.xlsx` enthaelt das Blatt `Feature 1 – Neuer Schüler`.

Dieses Blatt dient als visuelle Vorlage fuer die spaetere UserForm `frm_student_new`.

Enthalten sind:

- Fenstertitel
- Pflichtfelder Vorname, Nachname, Stammgruppe und Kurs
- Notizbereich
- Dokumentbereich mit Empty State
- Button `+ Dokument hinzufügen`
- Buttons Abbrechen und Speichern

### Auswirkungen

Zukuenftige UserForms duerfen nicht mehr frei gestaltet werden.

Die technische VBA-Umsetzung muss sich an der freigegebenen UX-Prototyp-Seite orientieren.

Validierung, Adapter-Anbindung und fachliche Schreibprozesse werden erst nach der UX-Freigabe umgesetzt.

### Abgrenzung

Diese Entscheidung fuehrt keine Implementierung ein.

Es wurden keine Python-Quellen, keine VBA-Quellen, keine UserForms, kein Build und kein Seed geaendert.

## ADR-042 - Worksheet-basierte Dialogseiten als primaeres Eingabe-Pattern

Status: Accepted

### Kontext

Feature 1 `Neuer Schueler` sollte urspruenglich als VBA-UserForm `frm_student_new` umgesetzt werden.

Die praktische Pruefung auf Microsoft Excel fuer macOS hat gezeigt:

- der lokale VBA-Editor bietet den UserForm-Designer nicht verlaesslich an
- automatisch erzeugte MSForms-Controls werden in der Zielumgebung nicht belastbar als sichtbare Dialogoberflaeche gerendert
- der UserForm-Testoeffner konnte zwar zuletzt starten, die angezeigte Maske blieb aber leer
- AppleScript-Tests mit `do Visual Basic` sind in diesem Projekt fuer diesen Pfad nicht belastbar

Der UserForm-Ansatz wird deshalb fuer Feature 1 nicht weiter als primaerer Eingabedialog verfolgt.

### Entscheidung

Primaeres Eingabe-Pattern fuer Excel auf macOS sind ab Feature 1 worksheet-basierte Dialogseiten.

Beispiel:

```text
dlg_neuer_schueler
```

Diese Dialogseiten:

- sehen wie modale Dialoge aus
- liegen als eigene geschuetzte Arbeitsblaetter in der Excel-Datei
- sammeln Eingaben
- enthalten keine Businesslogik
- schreiben nicht direkt in fachliche Tabellen
- rufen spaeter ueber VBA bzw. einen freigegebenen Adapter den Python Command Layer auf
- werden nach Speichern oder Abbrechen wieder verlassen

### Architecture Baseline v2.0

Die Baseline bleibt bestehen.

Der Adapter Layer kann in Excel ueber VBA-Navigation, worksheet-basierte Dialogseiten oder zukuenftige Adapter umgesetzt werden.

VBA enthaelt weiterhin keine Businesslogik.

Excel bleibt UI und Projektion, nicht fachliche Source of Truth.

### Status von `frm_student_new`

`frm_student_new.frm` bleibt vorerst als experimenteller Artefaktstand erhalten.

Die UserForm ist deprecated und nicht produktiv freigegeben.

Sie wird nicht geloescht, bis ein eigener Bereinigungs- oder Migrationsschritt freigegeben ist.

### Konsequenzen

Feature 1 verwendet `dlg_neuer_schueler` als neue technische Zieloberflaeche.

Der UX-Prototyp `output/Jenaplan_UX_Prototype_v0.1.xlsx`, Blatt `Feature 1 – Neuer Schüler`, bleibt die visuelle Referenz.

Validierung, Speichern, Python Command, SQLite-Schreibzugriff, Dokument-Upload und Refresh bleiben separate spaetere Features.

## ADR-043 - Runtime Adapter und Refresh Contract fuer `student.create`

Status: Accepted

### Kontext

Feature 1.4 `Schueler speichern` wurde gestoppt, weil zwar der Python-Stack fuer `student.create` bis SQLite validiert ist, aber der produktive Runtime-Pfad aus Excel und der Refresh der geoeffneten Arbeitsmappe noch nicht freigegeben waren.

Offene Fragen waren:

- Wie ruft Excel/VBA den Python Command Layer auf?
- Wie wird die geoeffnete Excel-Projektion nach erfolgreichem Speichern aktualisiert?
- Wie bleibt der Projection Builder alleiniger Eigentuemer der Projektion?
- Wie wird direkte Tabellen-Schreiblogik in VBA verhindert?

### Entscheidung: Runtime Adapter

Der produktive Runtime-Pfad fuer Feature 1 lautet:

```text
Worksheet-Dialogseite
-> VBA Adapter
-> Python CLI/Bridge
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Regeln:

- VBA liest Dialogwerte ausschliesslich ueber registrierte Named Ranges.
- VBA verwendet keine festen Zelladressen.
- VBA baut keine fachlichen IDs selbst.
- VBA validiert keine Fachregeln.
- VBA schreibt nicht direkt in SQLite.
- VBA schreibt nicht direkt in fachliche Workbook-Tabellen.
- Die Python CLI/Bridge ist Adapter zur Application-Schicht und enthaelt keine Fachlogik.
- Der Dispatcher ruft den registrierten `student.create`-Handler auf.
- `StudentService` bleibt Ort der fachlichen Regeln.
- `SQLiteStudentRepository` bleibt Ort des Schreibzugriffs auf SQLite.

### Entscheidung: Refresh Contract

Der primaere Refresh-Vertrag ist Option C:

```text
Python Command erfolgreich
-> SQLite aktualisiert
-> Python Projection Builder erzeugt Projection-Refresh-Paket
-> VBA importiert ausschliesslich Projection Output in die geoeffnete Arbeitsmappe
-> Excel zeigt aktualisierte Projektion
```

Das Projection-Refresh-Paket ist ein von Python erzeugtes technisches Artefakt.

Es enthaelt ausschliesslich Builder-Output fuer registrierte Projektionsziele.

VBA darf daraus nur kopieren:

- registrierte `data_*`-/`tbl_*`-Projektionskopien, soweit sie aus SQLite erzeugt wurden
- registrierte UI-Projektionsbereiche und Named Ranges
- temporaeren UI-State wie Suchfeld und Dialogeingaben zuruecksetzen

VBA darf dabei nicht:

- Projektionen selbst sortieren, filtern oder berechnen
- fachliche IDs erzeugen
- fachliche Daten pruefen
- direkt SQLite lesen oder schreiben
- `tbl_students` als fachliche Source of Truth behandeln

SQLite ist fuer diesen Schreibprozess die fachliche Source of Truth.

Die Excel-Arbeitsmappe enthaelt nach dem Refresh nur eine Projektion aus SQLite.

Der Projection Builder bleibt Eigentuemer der Projektion.

### Bewertete Alternativen

Option A: Python erzeugt eine neue `output/latest.xlsm`, Benutzer oeffnet neu.

- Zulaessig als Fallback.
- Nicht primaer, weil der geoeffnete Workflow unterbrochen wird und Feature 1.4 nach erfolgreichem Speichern zur Stammgruppenuebersicht zurueckkehren soll.

Option B: VBA liest aktualisierte Daten direkt aus SQLite und baut die Ansicht.

- Abgelehnt.
- Das wuerde SQLite-Zugriff und Projektionslogik nach VBA verschieben.

Option C: Python erzeugt strukturierte Projektion, VBA aktualisiert nur Projektionsbereiche.

- Akzeptiert.
- Erhaelt Python als fachliche Schreib- und Projection-Builder-Schicht.
- Erlaubt Aktualisierung der geoeffneten Arbeitsmappe ohne direkte fachliche Tabellenlogik in VBA.

### Fehlerfall

Wenn der Python Command fehlschlaegt:

- SQLite bleibt konsistent.
- Es wird kein Projection-Refresh-Paket importiert.
- Der Dialog bleibt geoeffnet.
- VBA zeigt nur die Fehlermeldung aus dem Adapter-Ergebnis an.
- Dialogwerte bleiben erhalten.

Wenn der Command erfolgreich ist, aber der Projection Refresh fehlschlaegt:

- SQLite bleibt erfolgreich aktualisiert.
- VBA darf keine eigene Projektion erzeugen.
- VBA zeigt eine technische Refresh-Fehlermeldung.
- Option A darf als Fallback angeboten werden: neu erzeugte Arbeitsmappe oeffnen.

### Konsequenzen fuer Feature 1.4

Feature 1.4 darf produktiv implementiert werden, wenn es diesen Vertrag einhaelt:

- Dialogwerte nur ueber Named Ranges
- VBA Adapter ohne Fachlogik
- Python CLI/Bridge als Adapter zum Dispatcher
- `student.create` ueber bestehenden Application-/Domain-/Repository-Stack
- SQLite als Source of Truth
- Refresh nur ueber Python-generierten Projection Output
- keine direkte fachliche Tabellenbearbeitung durch VBA

## ADR-044 - PySide6 Desktop-App-Spike als alternativer UI-Adapter validiert

Status: Validated Spike

### Kontext

Der Excel/VBA-Runtime-Adapter fuer `student.create` wurde bis SQLite umgesetzt, zeigte aber auf macOS eine hohe technische Reibung beim Prozessstart und bei stabilen Dialogoberflaechen.

Vor einer weiteren Vertiefung des Excel/VBA-Runtime-Pfads wurde auf Branch `spike/python-gui` ein alternativer Desktop-Adapter geprueft.

Ruecksprungpunkt fuer den Excel-/xlwings-Pfad:

- `checkpoint-excel-adapter-before-python-gui`

### Validierter Pfad

Der PySide6-Spike wurde manuell validiert.

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Nachgewiesener Stand:

- App startet.
- Maske `Neuer Schüler` funktioniert.
- Ein Schuelerdatensatz wurde in SQLite geschrieben.
- Speichern nutzt den bestehenden Application-/Service-/Repository-Stack.
- Tests sind gruen: `python3 -m pytest` mit 26 bestandenen Tests.
- Build ist gruen.
- Commit `5363e18` und Tag `spike-pyside6-student-create` sichern den Spike-Stand.

### Regeln

PySide6 ist ein validierter alternativer UI-Adapter.

Die GUI darf:

- Daten anzeigen
- Eingaben sammeln
- Commands erzeugen
- den `ApplicationCommandDispatcher` aufrufen
- Fehler sichtbar anzeigen

Die GUI darf nicht:

- Businesslogik enthalten
- fachliche IDs erzeugen
- direkt aus Widgets in SQLite schreiben
- Services, Validatoren oder Repositories umgehen
- Excel/VBA/Builder/Seed-Dateien loeschen oder ersetzen

### Auswirkungen

Excel/VBA bleibt im Repository erhalten.

Excel bleibt bestehende Projektion und moeglicher Export-/Berichtspfad.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut.

Die Architecture Baseline v2.0 bleibt gueltig: Adapter sind austauschbar, Python bleibt fachliche Schreibschicht, SQLite bleibt Source of Truth, der Projection Builder bleibt Eigentuemer der Excel-Projektion.

### Offen

Historischer Stand: Diese offenen Punkte wurden durch ADR-046 fuer die Hauptanwendung entschieden.

Weiterhin offen bleiben produktiver Nutzer-Datenbankpfad, Backup/Restore, Packaging als macOS-App, Updates, Migrationen und der genaue Umfang kuenftiger Excel-Exporte.

Naechste Pruefpunkte:

- UX Hauptfenster
- Schuelerprofil
- Beobachtungsmaske
- Packaging als macOS-App
- Datenbankpfad produktiv
- Backup/Restore
- Excel-Export/Berichte

## ADR-045 - PySide6 als Hauptanwendung und Icon-basierte visuelle Leitlinie

Status: Accepted

### Kontext

Der PySide6-Spike wurde ueber mehrere Sprints zu einer nutzbaren Desktop-App-Linie erweitert.

Das freigegebene App-Icon gibt eine klare visuelle Richtung vor: Wachstum, Schuelerbezug, Kompetenzentwicklung und Auswertung in einer ruhigen, hochwertigen Desktop-App.

Die Excel-/VBA-Linie bleibt technisch wertvoll, erzeugt aber nicht die gewuenschte moderne Hauptanmutung fuer die Anwendung.

### Entscheidung

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Neue UI-Entwicklung konzentriert sich auf die PySide-App.

Excel/VBA ist nicht mehr die Zielrichtung fuer die Haupt-App. Excel kann weiterhin als Export-, Berichts- oder Legacy-Projektion bestehen.

Das freigegebene App-Icon ist die zentrale gestalterische Referenz fuer die Anwendung.

Leitregel:

> Der Jenaplan Kompetenzmanager wirkt wie eine moderne paedagogische Entwicklungs-App: ruhig, klar, wachstumsorientiert, datenbewusst und freundlich.

### Konsequenzen

- Neue Screens orientieren sich visuell an der Icon-Farbwelt und Symbolik.
- Die PySide-App soll nicht wie klassische Verwaltungssoftware oder Excel wirken.
- Dunkelblau, Blau, Tuerkis, Gruen, Orange und helle neutrale Hintergruende bilden die kuenftige Designrichtung.
- Karten, Panels, Dialoge, Profile, Beobachtungen und Auswertungen duerfen eine leichte moderne Glasoptik nutzen, solange Lesbarkeit und Kontrast gewahrt bleiben.
- Fachlogik bleibt ausserhalb der GUI in Application, Domain und Infrastructure Layer.
- Excel/VBA wird nicht geloescht, aber als Haupt-App-Pfad nicht weiter priorisiert.

## ADR-046 - PySide wird Hauptanwendung; Excel/VBA wird Legacy/Export

Status: Accepted

### Kontext

Das Projekt startete mit Excel, openpyxl und spaeter einem validierten VBA-Seed als schneller Prototyp- und Projektionspfad.

Der PySide-Prototyp hat sich ueber mehrere Sprints als deutlich geeigneter fuer eine ruhige, hochwertige und moderne paedagogische Desktop-App erwiesen.

Excel/VBA verursacht auf macOS relevante Plattform-, Automatisierungs- und Stabilitaetsrisiken, insbesondere bei UserForms, VBA-Automation und Smoke-Test-Pfaden.

Der Product Owner hat entschieden, dass PySide die Hauptanwendung des Jenaplan-Kompetenzmanagers wird.

### Entscheidung

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Excel ist nicht mehr Hauptanwendung.

Excel bleibt nur:

- Legacy-Artefakt
- Referenz aus der fruehen Projektphase
- Exportformat
- spaetere Berichtsausgabe, falls fachlich sinnvoll

Excel ist nicht mehr:

- primaere UI
- produktive Datenquelle
- Entwicklungsziel fuer neue Features
- Testziel fuer UI-Funktionalitaet

VBA wird nicht weiterverfolgt.

VBA wird nicht mehr verwendet fuer:

- neue Features
- UI
- Smoke-Tests
- Automatisierung
- produktive Workflows

### Konsequenzen

- Neue Features werden in PySide umgesetzt.
- Neue fachliche Daten laufen ueber Application, Domain, Repository und SQLite.
- Keine neuen VBA-/Excel-UI-Features.
- Keine VBA-Smoke-Tests als Zielpfad.
- Roadmap und Dokumentation werden auf PySide ausgerichtet.
- Excel-Generatoren, Workbook-Code, Seeds und VBA-Quellen werden nicht sofort geloescht, aber als Legacy-/Export-Pfad behandelt.
- `openpyxl` bleibt erlaubt, wenn ausdruecklich Export, Bericht oder Legacy-Altstand betroffen ist.
- Spaeter kann eine gezielte Bereinigung, Archivierung oder Entfernung alter Excel-/VBA-Pfade erfolgen.
- Packaging, Installer, Backup/Restore, Datenbankpfad und SQLite-Migrationen bleiben eigene spaetere Entscheidungen.

## ADR-047 - Excel/VBA wird aus dem aktiven Projektpfad archiviert

Status: Accepted

### Kontext

Nach der PySide-/SQLite-Entscheidung liegen aktive Produktentwicklung, Persistenz, Fachlogik, UI, Berichte und Tests in der PySide-Hauptanwendung.

Die frueheren Excel-/openpyxl-/VBA-Dateien wurden im aktiven Root nicht mehr fuer neue Features benoetigt und erschwerten die Projektstruktur sowie die Standardchecks.

### Entscheidung

Reine Excel-/VBA-Legacy-Dateien werden unter `legacy/excel/` archiviert.

Der alte Workbook-Build `build.py`, openpyxl-Projektionen, VBA-Quellen, Seed-Arbeitsmappen und zugehoerige Hilfsskripte gehoeren nicht mehr zum aktiven App-Pfad.

`python3 build.py` ist kein Pflichtcheck mehr.

Der aktive Standardcheck ist:

```text
git diff --check
python3 -m pytest
QT_QPA_PLATFORM=offscreen python3 -c 'from src.desktop_app.main import main; print("import ok")'
```

### Konsequenzen

- PySide/SQLite bleibt die Hauptanwendung und Source of Truth.
- `openpyxl` wird aus den aktiven Runtime-Abhaengigkeiten entfernt, solange kein aktiver Exportpfad es nutzt.
- Runtime- und Output-Dateien bleiben unversioniert.
- Excel-/VBA-Artefakte bleiben historisch nachvollziehbar, werden aber nicht fuer neue Features, UI, Smoke-Tests oder Standardbuilds verwendet.
- Ein spaeterer Exportauftrag muss neu fachlich und technisch freigegeben werden.

## ADR-048 - Fachliche Stufenzuordnung fuer Lehrplan-Kompetenzen

Status: Accepted

### Kontext

Sprint 4 bildet die Grundschul-Lehrplaene fachweise in beobachtbare Kompetenzen ab.

Die Lehrplaene unterscheiden haeufig Schuleingangsphase, Klassenstufe 4 oder fachliche Progressionen, die nicht in jedem Fach sauber trennbar sind.

Der Kompetenzkatalog muss diese Progression spaeter abbilden, ohne jahrgangsgemischte Gruppen oder individuelle Lernwege einzuschraenken.

### Entscheidung

Kompetenzen werden fachlich einer Lernstufe zugeordnet:

- `Klassenstufe 1-3`
- `Klassenstufe 4`
- `stufenuebergreifend`

`stufenuebergreifend` wird verwendet, wenn eine eindeutige Trennung fachlich nicht moeglich oder nicht sinnvoll ist.

Die spaetere UI filtert Kompetenzen, sperrt sie aber nie.

Die Standardansicht zeigt passende Kompetenzen. Klassenstufe 1-3 und Klassenstufe 4 werden unterscheidbar filterbar. Zusaetzlich gibt es `Alle Kompetenzen anzeigen`.

Klasse-4-Kompetenzen bleiben auch fuer juengere Kinder auswaehlbar.

### Konsequenzen

- Die Stufe ist eine fachliche Katalogeigenschaft.
- Die technische Speicherung wird spaeter entschieden.
- Jetzt entstehen keine CSV-Aenderung, keine SQLite- oder Schemaaenderung und keine UI-Umsetzung.
- Bestehende Kompetenz-IDs bleiben unveraendert.
- Bestehende Beobachtungen werden nicht migriert.
- Die Logik unterstuetzt jahrgangsgemischte Gruppen und individuelle Lernwege.

## ADR-049 - Produktbezogene Katalogstufe getrennt von Quellen-Geltungsbereich

Status: Accepted

### Kontext

Der aktuelle CSV-Katalog fuehrt `grade_band` als quellenbezogenen Geltungsbereich. Im bestehenden Katalog steht dort durchgaengig `1-4`.

Die Product-Owner-Entscheidung zur Stufenlogik verlangt dagegen eine spaetere Produktfilterung nach `Klassenstufe 1-3`, `Klassenstufe 4` und `stufenuebergreifend`.

Diese Filterlogik ist nicht identisch mit dem Quellenfeld `grade_band`.

### Entscheidung

`grade_band` bleibt Quellen- und Lehrplankontext.

Fuer die produktbezogene Filterlogik wird das technische Feld `learning_stage` empfohlen.

Empfohlener Wertebereich:

- `stage_1_3`
- `stage_4`
- `cross_stage`

Die sichtbaren UI-Texte werden daraus abgeleitet und bleiben deutsch.

### Konsequenzen

- Sprint 4A ergaenzt den CSV-Katalog um `learning_stage`.
- Sprint 4A migriert SQLite `competencies` um `learning_stage` und die Katalogmetadaten `catalog_status`, `catalog_default_active` und `activation_group_key`.
- `active` bleibt lokale Aktivitaet.
- `catalog_default_active` speichert den Standardwert aus dem Katalog.
- `activation_group_key` dient optional aktivierbaren Bereichen.
- `catalog_status` sieht zunaechst ausschliesslich `current` und `legacy` vor.
- UI, Berichte, Schuelerprofil, Dashboard und Dokumentationsstand koennen nach fachlicher Passung filtern, ohne Kompetenzen zu sperren.
- Bestehende Beobachtungen, bestaetigte Kompetenzstaende und Kompetenz-IDs werden nicht migriert.
- `grade_band` darf nicht fuer die App-Filterlogik ueberladen werden.
- Der idempotente Katalog-Upsert muss lokale Aktivierungsentscheidungen weiter schuetzen.

## ADR-051 - Schnellbeobachtung ohne Kompetenzzuordnung

Eine Schnellbeobachtung ist eine bewusst kompetenzfreie aktive Beobachtung mit verpflichtender, nichtleerer Notiz. Sie wird ohne Eintraege in `observation_competency_ratings` gespeichert; ein neues SQLite-Feld ist nicht erforderlich, weil der produktive Schreibprozess Beobachtungen ohne Kompetenzbewertung zuvor nicht zuliess und der Zustand damit eindeutig ist.

Eine spaetere Kompetenzzuordnung und Bewertung ist im normalen Bearbeitungsdialog moeglich. Es erfolgt weder beim Speichern noch spaeter eine automatische Zuordnung oder Bewertung. Sobald eine Kompetenz ergaenzt wird, gelten wieder die normalen Kompetenz- und Bewertungsregeln.

Kompetenzfreie Schnellbeobachtungen erscheinen im Beobachtungsverlauf, wirken mangels Rating-Zeilen aber nicht auf Kompetenzstatus, Dokumentationsfortschritt, Diagramme oder Bestaetigungslogik und erzeugen keine Kompetenz- oder Entwicklungsinformation fuer Berichte.

## ADR-052 - Persistenter Berichtsentwurf ist keine finale Berichtsdomain

Sprint 7F.1 fuehrt fuer Lernentwicklungsberichte einen persistenten Arbeitsentwurf mit Status `draft` ein. Der Entwurf speichert manuelle Texte und bewusste Auswahlreferenzen, damit Laura die Berichtswerkstatt schliessen und spaeter weiterbearbeiten kann.

Der Entwurf ist bewusst von einer spaeteren finalen Berichtsentitaet getrennt:

- keine Freigabe oder Pruefung
- keine Versionierung oder Archivierung
- kein eingefrorener Ausgabestand
- keine Signatur oder Empfaengerverwaltung
- keine eigene Kompetenzbewertung

Kompetenzen und Beobachtungen werden ausschliesslich ueber ihre stabilen IDs referenziert. Texte, Hierarchie, Bewertungen, Bestaetigungen, Beobachtungsdatum, Kontext und Notiz bleiben in ihren bestehenden Sources of Truth. Beim Laden werden diese Informationen erneut ueber die kanonische Kompetenz- und Beobachtungsprojektion aufgeloest.

Die persistente Entwurfsstruktur besteht aus `report_drafts` und normalisierten Relationstabellen fuer Faecher/Fachtexte, Kompetenzen, Beobachtungen und Diagramme. Anlegen und Aktualisieren erfolgen atomar ueber ViewModel, Application Layer, Domain-Service und Repository. `ReportOutputModel` und `PdfRenderer` bleiben reine Ausgabeschicht und kennen die Entwurfstabellen nicht.

Eine spaetere Freigabe-, Versions- oder Archivierungsdomain benoetigt eine neue Product-Owner- und Datenmodellentscheidung und darf nicht durch zusaetzliche Statuswerte in diesen Sprint hineingezogen werden.
