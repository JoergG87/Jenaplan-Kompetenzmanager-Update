# Design-System

Das freigegebene App-Icon ist ab der PySide-Hauptanwendung die zentrale gestalterische Referenz fuer den Jenaplan-Kompetenzmanager.

Das aktuelle Design der Stammgruppenübersicht wurde durch Laura freigegeben.

Dieses Design ist die verbindliche Referenz für alle zukünftigen Ansichten.

Neue Screens sollen visuell an das App-Icon anschliessen.

Leitregel:

> Der Jenaplan Kompetenzmanager wirkt wie eine moderne paedagogische Entwicklungs-App: ruhig, klar, wachstumsorientiert, datenbewusst und freundlich.

## Verbindliche Eigenschaften

Zum freigegebenen Design gehören:

- Bezug zum freigegebenen App-Icon
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

- PySide-Hauptnavigation
- Dashboard / Startseite
- Schuelerliste
- Stammgruppenübersicht
- Kursübersicht
- Schülerprofil
- Beobachtungsdialoge
- Stammdaten
- Kompetenzansichten
- Auswertungen und Berichte
- App-Info und Statusbereiche
- zukünftige Verwaltungsansichten
- zukünftige Dialoge, Dialogseiten und experimentelle UserForms

## App-Icon als visuelle Leitlinie

Das App-Icon verbindet Baum, Personen, Diagramm und schützenden Bogen zu einem ruhigen, hochwertigen Zeichen fuer paedagogische Entwicklungsarbeit.

Die Anwendung soll daraus folgende Grundidee ableiten:

- modern, ruhig, freundlich und professionell
- klar strukturiert, aber nicht administrativ schwer
- wachstumsorientiert und schuelerbezogen
- datenbewusst, ohne technisch-kuehle Verwaltungsoptik
- hochwertig wie eine moderne Desktop-App, nicht wie eine klassische Excel- oder Tabellenanwendung

Die Gestaltung soll Wachstum, Schuelerbezug, Kompetenzentwicklung und Auswertung gleichzeitig sichtbar machen.

### Bedeutungsanker

- Baum: Wachstum, Lernentwicklung und langfristige Kompetenzentwicklung
- Personen: Schuelerbezug, paedagogische Beziehung und konkrete Arbeit mit Kindern
- Diagramm: Auswertungen, Kompetenzverlaeufe und Berichte
- Kreis/Bogen: Ganzheitlichkeit, Ueberblick, Schutzraum und strukturierter Rahmen
- farbige Blaetter: individuelle Lernwege und unterschiedliche Entwicklungsfelder

Diese Bedeutungsanker sollen bei spaeteren UI-Entscheidungen beruecksichtigt werden.

### Farbwelt aus dem Icon

Die Icon-Palette ist die Grundlage fuer die kuenftige PySide-Oberflaeche.

- Dunkelblau: Struktur, Professionalitaet, Navigation, Auswertung
- Blau: Klarheit, Kompetenzentwicklung, Berichte
- Tuerkis: Entwicklung, Uebergaenge, Lernverlaeufe
- Gruen: Wachstum, Lernen, Foerderung
- Orange: Aktivitaet, Beobachtung, paedagogischer Impuls
- helle neutrale Hintergruende: Ruhe, Lesbarkeit, Konzentration

Die Farben werden nicht grell oder verspielt eingesetzt. Sie sollen modern, ausgewogen und hochwertig wirken.

Kursfarben, Diagrammfarben, Statusmarker und Aktionsfarben sollen sich aus dieser Icon-Farbwelt ableiten.

### Formensprache

Die App verwendet eine weiche, leichte Formensprache:

- abgerundete Formen
- Kartenoptik statt Tabellenoptik, wo sinnvoll
- grosszuegige Abstaende und Weissraum
- klare visuelle Hierarchie
- freundliche Icons und Marker
- ruhige, moderne Oberflaechen
- keine ueberladene Verwaltungsoptik
- keine harte Tabellen- oder Excel-Anmutung als Hauptstil

Schuelerprofile sollen als ruhige Karten mit klaren Bereichen erscheinen.

Beobachtungen sollen bevorzugt als leichte Cards oder geordnete Listen mit klarer Hierarchie gestaltet werden, nicht als reine Tabellenlisten.

Auswertungen und Berichte sollen Diagrammfarben aus der Icon-Palette verwenden.

Wichtige Aktionen duerfen farblich klar hervorgehoben werden, bleiben aber zurueckhaltend und serioes.

### Moderne leichte Glasoptik

Wenn technisch und gestalterisch sinnvoll umsetzbar, darf die PySide-App eine leichte moderne Glasoptik aufgreifen.

Gemeint ist:

- helle, leicht transparente oder weich abgesetzte Flaechen
- dezente Schatten
- sanfte Rahmen
- leicht schwebende Karten und Panels
- ruhige, helle Hintergruende
- moderne Tiefe ohne starke Effekte

Glasoptik ist ein Stilmittel, kein Selbstzweck.

Verbindliche Grenzen:

- Lesbarkeit hat Vorrang.
- Kontraste muessen barrierearm bleiben.
- Transparenzen duerfen Texte nicht schwer lesbar machen.
- Keine uebertriebene Glassmorphism-Optik.
- Die App bleibt serioes und paedagogisch professionell.

### Zu vermeiden

- keine Excel- oder Tabellenoptik als Hauptanmutung
- keine ueberladene Admin-Oberflaeche
- keine grellen Primaerfarben
- keine unruhigen Verlaeufe
- keine uebertriebene Glasoptik
- keine verspielte Kinder-App-Optik
- keine schlechte Lesbarkeit durch Transparenzen
- keine Designaenderungen ohne Bezug zur Icon-Farbwelt

## PySide-Hauptanwendung

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Neue UI-Entwicklung konzentriert sich auf die PySide-App.

Excel/VBA ist nicht mehr die Zielrichtung fuer die Haupt-App. Der alte Excel-/VBA-Stand liegt nur noch im Legacy-Archiv `legacy/excel/`; neue UI-Entwicklung konzentriert sich auf PySide.

### PySide Theme Umsetzung

Die freigegebene Icon-Leitlinie wird in der PySide-App ueber ein zentrales Theme-Modul umgesetzt.

Das Theme buendelt:

- die Icon-Farbwelt fuer Navigation, Primäraktionen, Statusmarker und ruhige Flaechen
- helle neutrale App-Hintergruende
- weiche Karten- und Panel-Flaechen mit sanften Rahmen
- einheitliche Tabellen-, Eingabe- und Button-Stile
- semantische Textrollen fuer App-Titel, Screen-Titel, Dialogtitel, Kartenueberschriften, Hinweise und Fehlermeldungen

Neue PySide-Screens und Dialoge sollen dieses Theme verwenden, statt eigene Farb- oder Kartenstile lokal zu definieren.

Das App-Icon wird als sichtbares Branding in der PySide-Hauptanwendung verwendet:

- klein und ruhig oberhalb der Hauptnavigation in der Seitenleiste
- groesser und zentriert oben im App-Info-Dialog

Das Icon ist Branding und Bedeutungsanker, keine dekorative Ueberladung. Es darf die Navigation, Dialogtexte oder fachliche Inhalte nicht verdecken.

Die leichte Glasoptik wird technisch ueber helle, weich abgesetzte Flaechen, sanfte Rahmen und dezente Kontraste simuliert. Echte macOS-Transparenz oder schwer wartbare Spezialwidgets sind nicht Bestandteil des Design-Systems.

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
