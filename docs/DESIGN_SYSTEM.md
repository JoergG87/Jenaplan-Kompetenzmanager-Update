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

Grundregeln:

- klare Ueberschrift
- einspaltige, gut lesbare Pflichtfelder
- Pflichtfelder sichtbar mit `*`
- ruhige Abstaende
- keine ueberladene Informationsdichte
- primaere Aktion rechts unten
- Abbrechen links neben Speichern
- Dokumentbereiche als einfache Listen mit klarer Hinzufuegen-Aktion

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
