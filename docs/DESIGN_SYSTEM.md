# Design-System

## Kindbezogene Workspace-Sprache - UI Sprint 4

Schuelerprofil, Kompetenz-Cockpit und Beobachtungsdialog bilden einen zusammenhaengenden paedagogischen Workspace. Die Hierarchie ist verbindlich: zuerst Kind und aktueller Kontext, danach primaere paedagogische Information, relevante Aktion, sekundaere Details und zuletzt historische beziehungsweise ergaenzende Inhalte. Der Kindername bleibt im Profilkopf und im Dialog-`PageHeader` dauerhaft sichtbar. Im Profil markiert genau eine blaue Primaeraktion `Neue Beobachtung`; Datei und seltenere bestehende Aktionen bleiben sekundaer.

Das Profil nutzt `AppCard[accent]` fuer den kompakten Kindkontext, `SegmentedControl` fuer die lokale Navigation sowie `SectionHeader`, `FilterBar`, `SearchField`, `FilterChip`, `StatusBadge` und `EmptyState` fuer bestehende Inhalte. Beobachtungen erscheinen als scanbare Kartenzeilen: Datum und Fach bilden den Kopf, Kontext und Notiz bleiben darunter ruhig, Details und Bearbeiten sind bewusst erreichbar. Leere Beobachtungslisten bieten genau die naechste sinnvolle Aktion an.

Im Kompetenz-Cockpit wird Hierarchie auch ohne Farbe ueber Einrueckung, Typografie, Abstand und Surface unterschieden. Fach nutzt eine ruhige Akzentflaeche, Kompetenzbereich eine weiche Flaeche, Thema eine normale Flaeche und die Kompetenz eine linksbuendige Disclosure-Zeile. Lange Kompetenztexte umbrechen in Details und Auswahllisten. Neutrale Fortschrittsbalken und Zaehler beschreiben ausschliesslich Dokumentationsabdeckung; historische Zeilen tragen eine eindeutige ruhige Kennzeichnung.

Der Beobachtungsdialog behaelt drei Zonen: `Kind und Kontext`, `Ausgewaehlte Kompetenzen / Kompetenzkatalog` sowie `Beobachtung / Dokumente / Aktionen`. Der Katalog nutzt dieselbe Segment-, Such-, Card- und Badge-Sprache. Ausgewaehlte Kompetenzen zeigen Bewertung immer sichtbar als vier beschriftete Chips. Dateizeilen zeigen Dateiname, Typ und eine klar benannte Entfernen-Aktion. `InlineMessage` steht unmittelbar vor der persistenten Speicherleiste.

Disclosure setzt Sichtbarkeit und Datenzustand sofort und verwendet nur eine zentrale Opacity-Bestaetigung von maximal `MOTION_FAST_MS`. Keine Hoehenanimation langer Listen, keine verschachtelten Animationen und kein Layoutflackern. Reduced Motion zeigt den Endzustand unmittelbar. Die Arbeitsbereiche werden fuer 1400 x 900, 1280 x 800 und 1180 x 760 geprueft; Pflichtaktionen bleiben sichtbar, der Dialog besitzt getrennte vertikale Scrollbereiche und keinen horizontalen Katalog- oder Gesamtscroll.

Accessibility-Regel: lokale Navigation und Klassenstufenfilter sind per Pfeiltasten bedienbar; Disclosure, Kompetenzwahl und Bewertung reagieren auf Fokus sowie Enter/Space; Datum, Fach, Kontext, Notiz, Suche, Bewertung, Entfernen und Speichern besitzen Accessible Names. Keine Information wird ausschliesslich durch Farbe vermittelt.

QPainter-Regel: UI Sprint 4 verwendet keinen QPainter. Timeline-Marker, Spezial-Focus-Ringe oder Evidenzgrafiken erzeugen gegenueber den vorhandenen Standardwidgets keinen ausreichenden Mehrwert; zentrale Qt-Widgets und QSS bleiben High-DPI-, Fokus- und Reduced-Motion-sicherer.

## Motion System - UI Sprint 3

Motion unterstuetzt Orientierung und Rueckmeldung, ohne Arbeitsablaeufe zu verlangsamen. Die zentrale Implementierung liegt in `src/desktop_app/motion.py`; Screens besitzen keine eigene Animationslogik. Verbindliche Dauern bleiben `120 ms` fuer direkte Rueckmeldung, `180 ms` fuer normale Uebergaenge und `240 ms` nur fuer groessere, seltene Zustandswechsel. Standard-Easing ist `OutCubic`, Ausblendungen verwenden `InCubic`.

Die globale `MotionPolicy` besitzt genau einen Reduced-Motion-Schalter. Im reduzierten Modus werden fachlicher Zustand, Sichtbarkeit, Fokus und Endwerte sofort gesetzt. Timer duerfen weiterhin die Lesedauer einer Meldung steuern, erzeugen aber keine Bewegung. Animationen werden pro Widget und semantischem Schluessel ersetzt statt gestapelt; Qt-Ownership und Aufraeumen bei Abschluss beziehungsweise Widget-Zerstoerung sind Bestandteil des zentralen Vertrags. Eine spaetere verlaessliche Qt-/Plattformanbindung setzt ausschliesslich diese Policy und erfordert keine Aenderung an Komponenten; UI Sprint 3 erzwingt dafuer keine neue sichtbare Einstellung.

Komponenten mit Motion:

- `AppCard` nur bei `interactive`: dezenter, layout-neutraler Hover-Schatten; Pressed, Fokus und Auswahl bleiben sofort sichtbar
- `SegmentedControl`: kurze Opacity-Bestaetigung des bereits gesetzten Zielsegments; Signal und Navigation werden nicht verzoegert
- `FilterChip`: Einblenden eines neu sichtbaren Filterzustands; Reset und Filterausfuehrung bleiben unmittelbar
- `InlineMessage`: ruhiges Einblenden neuer Information oder Erfolgsmeldung; Warnungen und Fehler erscheinen sofort
- `Toast`: Ein-/Ausblenden, Hover-Pause und sichere Ersetzung einer laufenden Meldung

Bewusst statisch bleiben `EmptyState`, Tabellen und Tabellenzeilen, globale Navigation, Search-Ergebnisse sowie nicht interaktive Karten. UI Sprint 4 nutzt fuer die wiederkehrenden Kompetenz-Disclosures ausschliesslich sofortige Sichtbarkeit plus kurze zentrale Opacity-Bestaetigung; Dialog-Fades, Hoehenanimationen und verschachtelte Listenanimationen bleiben ausgeschlossen. Es gibt keine Screen-Uebergaenge, Feder-/Bounce-Effekte, Geometrieanimationen oder blockierende Animationen.

## Component Library V2 - UI Sprint 2

Bestandskomponenten, die erweitert werden:

- `PageHeader`: klare Titel-/Untertitelhierarchie und stabile Aktionszone
- `SearchField`: Suchicon, native Clear-Aktion, Escape-Reset und sichtbarer Fokus
- `StatusBadge`: semantische, aber fachlich neutrale Tones
- `EmptyState`: optionale Ueberschrift, Erklaerung und genau eine passende Aktion
- `SegmentedControl`: kompakte lokale Navigation mit Maus, Fokus und Pfeiltasten
- `InlineMessage` und `Toast`: kontextgebundene beziehungsweise fluechtige Rueckmeldung

Neue notwendige Basiskomponenten:

- `AppCard`: Surface-Vertrag mit `default`, `soft`, `accent` und `interactive`; nur interaktive Karten erhalten Hover und Auswahlzustand
- `SectionHeader`: Abschnittstitel, optionale Kurzbeschreibung, Hilfe und Aktionen
- `FilterBar`: komponiert vorhandene Suche, aktive Filter und Reset, besitzt aber keine Filterlogik
- `FilterChip`: zeigt lokalen Filterstate; `selected`, Fokus und Disabled sind rein semantische UI-Zustaende
- `IconButton`: kompakte Aktion mit SVG-Icon, Tooltip und verpflichtendem Accessible Name

Bewusst nicht als eigene Komponenten eingefuehrt werden `DashboardCard`, `InfoCard`, `MetricCard`, `StudentRow` und `GroupCard`: Sie werden durch `AppCard`-Varianten, bestehende Qt-Tabellenzeilen und komponierte Screen-Inhalte belastbar abgedeckt. Eine Spezialklasse ohne zweiten Nutzungskontext waere nicht gerechtfertigt.

Surface-Hierarchie:

1. App-Hintergrund trennt globale Arbeitsflaechen.
2. `AppCard[cardVariant="default"]` bildet normale Inhaltsflaechen.
3. `soft` gruppiert sekundaere Informationen ohne zusaetzliche Elevation.
4. `accent` markiert genau eine primaere Situation, zum Beispiel die aktuelle beziehungsweise naechste Stunde.
5. `interactive` kennzeichnet klickbare Karten durch Cursor, Hover, Fokus und optional `selected`; nicht klickbare Karten reagieren nicht auf Hover.

Filterregel: Suche bleibt je Schuelerliste lokal. Der sichtbare Kontextfilter stammt aus dem bestehenden Shell-/Workspace-State. Reset erscheint nur fuer einen aktiven Kontextfilter und kehrt zur ausloesenden Auswahl zurueck. Ein Segmentwechsel laedt dessen bestehenden Kontext neu; es entsteht keine persistente oder parallele Filterhaltung.

QPainter-Regel: UI Sprint 2 verwendet keinen QPainter. Karten, Fokus, Chips, Tabellen, Timeline und Matrix lassen sich mit Standardwidgets und zentralem QSS hochwertig und High-DPI-sicher umsetzen. QPainter bleibt kuenftigen visuellen Elementen vorbehalten, fuer die Standardwidgets nachweislich nicht ausreichen.

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

Das Kompetenz-Cockpit im Schuelerprofil nutzt verschachtelte, abgerundete Karten und neutrale Fortschrittsbalken. Fortschritt visualisiert ausschließlich Dokumentationsabdeckung und verwendet keine Bewertungs- oder Ampelfarben. Die Darstellung erweitert das bestehende Kartensystem, ohne eine neue Farbsemantik oder ein spaeteres Designsystem vorwegzunehmen.

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

### UI Sprint 1: Design Tokens und Grundkomponenten

Die PySide-Hauptanwendung verwendet die native Systemschrift. Eine feste Schriftfamilie wie Arial wird nicht gesetzt. Semantische Typografierollen definieren Hierarchie, Gewicht und Groesse, ohne die Plattformtypografie zu ersetzen.

Verbindliche Token-Stufen:

- Abstaende: `4`, `8`, `12`, `16`, `24`, `32`, `48`
- Radien: klein, mittel, gross und extra gross
- Elevation: flach, Karte und Overlay; Tiefe bleibt dezent und dient nur der Hierarchie
- Motion: schnell `120 ms`, Standard `180 ms`, langsam `240 ms`; Animationen sind optional und duerfen Bedienung oder Tests nicht blockieren
- Farben: Hintergrund, Oberflaeche, Rahmen, Text, Fokus, Information, Erfolg, Warnung und Fehler werden semantisch benannt

Verbindliche Buttonrollen:

- `primary`: genau die wichtigste Seiten- oder Speicheraktion
- `secondary`: normale explizite Aktion
- `quiet`: untergeordnete Aktion ohne visuelles Gewicht
- `destructive`: bestaetigungspflichtige destruktive Aktion
- `icon`: kompakte Aktion mit zugaenglichem Namen und Tooltip
- `link`: Navigation innerhalb eines fachlichen Kontexts

Alle Rollen besitzen Normal-, Hover-, Fokus-, Pressed- und Disabled-Zustaende. Speichern bleibt primaer; Abbrechen bleibt sekundaer. Lokale Stylesheets duerfen fuer diese Interaktionsrollen nicht verwendet werden.

Registrierte Grundkomponenten sind `PageHeader`, `SegmentedControl`, `SearchField`, `StatusBadge`, `InlineMessage`, `EmptyState` und `Toast`. `NavigationItem` ist die semantische Definition eines Shell-Eintrags. Nicht blockierender Erfolg erscheint als Toast; dauerhaft handlungsrelevante Information, Warnung oder Validierung steht inline am betroffenen Kontext. Modale Dialoge bleiben fuer irreversible Bestaetigungen und Fehler, die ein Fortsetzen verhindern.

Die Shell verwendet ein konsistentes Outline-SVG-Set mit den Groessenrollen `16`, `20` und `24`. Zufaellige Unicode-Zeichen sind keine Shell- oder Aktionsicons. Fachlich variable Kursfarben werden als kleine neutrale Flaechenmarker dargestellt.

Fokus folgt der sichtbaren Arbeitsreihenfolge. Alle interaktiven Elemente sind per Tab erreichbar; segmentierte Navigation reagiert zusaetzlich auf Links/Rechts, Suche auf Escape und Tabellenaktivierung auf Enter beziehungsweise Doppelklick. Iconaktionen und nicht selbsterklaerende Controls erhalten zugaengliche Namen und Tooltips.

Dokumentationsabdeckung verwendet ausschliesslich neutrale Blau-Grau-Abstufungen. Sie ist keine Bewertung, keine Leistung und keine Ampel. Gruen, Orange und Rot duerfen in dieser Matrix keinen vermeintlich guten, mittleren oder schlechten Kompetenzstand codieren.

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
