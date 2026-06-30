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
- zukünftige Dialoge und UserForms

## Änderungsregel

Normale Entwicklungssprints verändern das Design nicht.

Designänderungen dürfen ausschließlich über einen eigenen UX-Sprint erfolgen.

Ein UX-Sprint benötigt:

- UX-Review
- Product-Owner-Freigabe
- anschließende dokumentierte Umsetzung

## Architekturregel

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.

Python erzeugt Benutzeroberflächen aus dem freigegebenen Design-System.

VBA implementiert ausschließlich Interaktion und verändert keine fachliche Logik.

## Modale UserForms

Modale UserForms folgen dem ruhigen, einfachen Desktop-App-Charakter des freigegebenen Designs.

Sie sind Eingabedialoge der Anwendung und keine Tabellenansichten.

Alle zukuenftigen Eingabemasken verwenden denselben Dialogstandard.

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

Referenzdialog `frm_student_new`:

- Zweck: neuen Schueler anlegen
- Rolle: erste Referenzimplementierung des Dialog Frameworks
- Status: nicht produktiv freigegeben
- Felder: Vorname *, Nachname *, Stammgruppe *, Kurs *, Notiz
- keine Speicherlogik
- keine StudentService-Anbindung
- kein Tabellenzugriff

Referenzskizze fuer `frm_student_new`:

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
