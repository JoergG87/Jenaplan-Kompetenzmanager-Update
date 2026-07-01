# Design-System

Das aktuelle Design der Stammgruppenübersicht wurde durch Laura freigegeben.

Dieses Design ist die verbindliche Referenz für alle zukünftigen Ansichten.

## Verbindliche Eigenschaften

Zum freigegebenen Design gehören:

- Farbwelt
- Typografie
- Kartenlayout
- Kartenabstände
- Desktop-App-Anmutung
- 140-%-Zoom der Stammgruppenübersicht
- Suchfeld
- Weißraum
- visuelle Hierarchie

## Geltungsbereich

Alle zukünftigen Ansichten müssen sich an diesem Design orientieren.

Das gilt insbesondere für:

- Stammgruppenübersicht
- Kursübersicht
- Schülerprofil
- zukünftige Verwaltungsansichten
- zukünftige Dialoge, Dialogseiten und experimentelle UserForms

## Änderungsregel

Normale Entwicklungssprints verändern das Design nicht.

Designänderungen dürfen ausschließlich über einen eigenen UX-Sprint erfolgen.

Ein UX-Sprint benötigt:

- UX-Review
- Product-Owner-Freigabe
- anschließende dokumentierte Umsetzung

## UX-Prototypen fuer Eingabedialoge

Neue Eingabedialoge werden nicht frei im VBA-Designer oder direkt im Workbook gestaltet.

Vor der technischen Umsetzung muss ein UX-Prototyp als verbindliche visuelle Referenz entstehen.

Der Ablauf lautet:

1. UX-Prototyp erstellen
2. UX-Review mit Laura bzw. Product Owner durchfuehren
3. UX-Freigabe dokumentieren
4. worksheet-basierte Dialogseite moeglichst 1:1 nach dem freigegebenen UX-Prototyp umsetzen
5. Validierung, Adapter-Anbindung und fachliche Logik erst danach ergaenzen

Der UX-Prototyp ist keine technische Implementierung. Er enthaelt keine VBA-Events, keine Validierung, keine Adapter-Anbindung, keine SQLite-Kommunikation und keine fachliche Logik.

Feature 1 `Neuer Schueler`:

- Die Datei `output/Jenaplan_UX_Prototype_v0.1.xlsx` enthaelt das Blatt `Feature 1 – Neuer Schüler`.
- Dieses Blatt ist die visuelle Vorlage fuer die worksheet-basierte Dialogseite `dlg_neuer_schueler`.
- Enthalten sind Fenstertitel, Pflichtfelder Vorname, Nachname, Stammgruppe und Kurs, Notizbereich, Dokumentbereich mit Empty State, Button `+ Dokument hinzufügen` sowie die Buttons Abbrechen und Speichern.

## Architekturregel

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.

Python erzeugt Benutzeroberflächen aus dem freigegebenen Design-System.

VBA implementiert ausschließlich Interaktion und verändert keine fachliche Logik.

## Worksheet-basierte Dialogseiten

Worksheet-basierte Dialogseiten sind ab Feature 1 das primaere Eingabe-Pattern fuer Excel auf macOS.

Sie folgen dem ruhigen, einfachen Desktop-App-Charakter des freigegebenen Designs.

Sie sind eigene geschuetzte Arbeitsblaetter, die wie Dialoge gestaltet sind.

Sie sammeln Eingaben, enthalten keine Businesslogik, schreiben nicht direkt in fachliche Tabellen und rufen spaeter ausschliesslich freigegebene Adapter auf.

Standard fuer `dlg_neuer_schueler`:

- sichtbarer Fenstertitel `Neuer Schüler`
- eigene Dialogseite `dlg_neuer_schueler`
- geschuetztes Arbeitsblatt mit freigegebenen Eingabebereichen
- einspaltiger Aufbau von oben nach unten
- Pflichtfelder sichtbar mit `*`
- Dokumentbereich als einfache Liste mit Empty State
- Buttons unten rechts: Abbrechen links, Speichern rechts
- Abbrechen navigiert spaeter zur aufrufenden Ansicht zurueck
- Speichern wird erst mit Validierung und Adapter-Anbindung produktiv

## Deprecated: Modale VBA-UserForms

Modale UserForms folgen dem ruhigen, einfachen Desktop-App-Charakter des freigegebenen Designs.

Sie sind Eingabedialoge der Anwendung und keine Tabellenansichten.

VBA-UserForms sind auf Excel fuer macOS nicht mehr das primaere Eingabe-Pattern.

`frm_student_new` bleibt als experimenteller Artefaktstand erhalten, ist aber nicht produktiv freigegeben.

Keine weiteren AppleScript-Tests mit `do Visual Basic` werden fuer UserForms verwendet.

Historischer Dialogstandard:

Standard-Fenster:

- Standardgroesse fuer einfache Eingabedialoge: ca. 5760 x 6720 Twips
- modales Oeffnen
- Titel ueber die Fenster-Caption, kurz und fachlich eindeutig
- einspaltiger Aufbau von oben nach unten
- linker und rechter Rand ca. 480 Twips
- vertikale Abstaende zwischen Label und Feld ca. 300 Twips
- groessere Abschnittsabstaende zwischen Feldgruppen

Standard-Labels:

- klare Ueberschrift
- einspaltige, gut lesbare Pflichtfelder
- Pflichtfelder sichtbar mit `*`
- Labels stehen direkt oberhalb des Eingabefelds
- sichtbare Labels sind fachliche Begriffe, technische IDs bleiben unsichtbar

Standard-Verhalten:

- Tab-Reihenfolge von oben nach unten
- Enter = Speichern
- Esc = Abbrechen
- keine Tabellenbearbeitung durch Lehrkraefte
- UserForms sammeln nur Eingaben und rufen spaeter freigegebene Services auf
- keine Businesslogik in UserForms
- kein direkter Schreibzugriff auf Workbook-Tabellen
- nach erfolgreichem Speichern schliesst sich die UserForm
- danach wird die betroffene Ansicht aktualisiert

Standard-Buttons:

- Standardbuttons: Abbrechen und Speichern
- Abbrechen links, Speichern rechts
- primaere Aktion rechts unten
- Abbrechen links neben Speichern

Layout-Regeln:

- ruhige Abstaende
- keine ueberladene Informationsdichte
- Dokumentbereiche als einfache Listen mit klarer Hinzufuegen-Aktion

Experimenteller Referenzdialog `frm_student_new`:

- Zweck: neuen Schueler anlegen
- Rolle: verworfener UserForm-Versuch fuer Feature 1
- Status: deprecated, nicht produktiv freigegeben
- Felder: Vorname *, Nachname *, Stammgruppe *, Kurs *, Notiz
- keine Speicherlogik
- keine StudentService-Anbindung
- kein Tabellenzugriff

Referenzskizze fuer `dlg_neuer_schueler`:

```text
+--------------------------------------------+
|              Neuer Schueler                |
+--------------------------------------------+
| Vorname *                                  |
| [__________________________]               |
|                                            |
| Nachname *                                 |
| [__________________________]               |
|                                            |
| Stammgruppe *                              |
| [v Eulen]                                  |
|                                            |
| Kurs *                                     |
| [v Kurs 2]                                 |
|                                            |
| Notiz                                      |
| +--------------------------------------+   |
| |                                      |   |
| +--------------------------------------+   |
|                                            |
| Dokumente                                  |
| [Dokument] Foerderplan.pdf                 |
| [Dokument] Hoergeraetebericht.pdf          |
| [+ Dokument hinzufuegen]                   |
|                                            |
|          [Abbrechen]   [Speichern]         |
+--------------------------------------------+
```

## Stammgruppenübersicht

Die sichtbare Startansicht heißt `Stammgruppenübersicht`.

Die Schülerkarten der Stammgruppenübersicht zeigen den Kurs des Schülers. Die Stammgruppe wird dort nicht erneut auf jeder Karte angezeigt, weil die Ansicht bereits genau eine Stammgruppe darstellt.

Die Kartenfarbe wird aus der Kurszuordnung abgeleitet. Die konkrete Farbwelt bleibt Teil des freigegebenen Grunddesigns.
