# UX Blueprint v1.0

## Lokaler Komfortzugang ab Sprint 0.2B.4a

Die Auth-Journey lautet: Restore-Recovery -> Auth-Gate -> gültiges ausdrücklich
aktiviertes Gerätecredential oder Passwort -> neue flüchtige Sitzung ->
fachliche Shell. `Auf diesem Gerät angemeldet bleiben` ist keine fortdauernde
Sitzung; App-Ende, manuelle Sperre, Inaktivität und Wake behalten ihre Wirkung.

Auf unterstützten Macs kann die Lehrkraft nach einer Sperre bewusst
`Mit Touch ID entsperren` wählen. Das Passwortfeld bleibt sichtbar. Abbruch,
Nichtverfügbarkeit oder Fehler führen ohne Wiederholungsloop zurück zum
Passwort. Aktivierung und Widerruf liegen ausschließlich in der vorhandenen
Sicherheits-Unterseite; es gibt keine neue Navigation und keine fachliche
Journey.

## 1. Ziel

Der erste Prototyp dient dazu, die zentralen Arbeitsabläufe der Lehrkraft als klaren, schnellen und nachvollziehbaren Bedienfluss abzubilden.

Der Fokus liegt auf der täglichen Arbeit im Unterricht und auf der direkten Erfassung von Beobachtungen.

Zielplattform ist Microsoft Excel für macOS.

## 2. UX-Leitlinien

- Single Purpose Views, siehe `ADR-012` in `DECISIONS.md`.
- Beobachtung ist die fachliche Source of Truth.
- Das Datenmodell ist die fachliche Grundlage; alle Ansichten sind Projektionen des Datenmodells.
- Das freigegebene Design-System ist die visuelle Source of Truth für sämtliche Benutzeroberflächen.
- Schnellste Aktion ist `Neue Beobachtung`.
- Fach -> Kompetenzbereich -> Thema -> Kompetenz.
- Unterricht vor Analyse.
- Minimalistische Informationsdarstellung.
- Component Library V2 nutzt eine ruhige Surface-Hierarchie: eine Akzentflaeche fuer die aktuelle Situation, normale Arbeitskarten und weiche sekundaere Informationsflaechen.
- Suche und aktive Kontextfilter werden gemeinsam sichtbar; Reset erscheint nur bei tatsaechlich aktivem Kontextfilter.
- Motion bestaetigt nur bereits ausgefuehrte Interaktionen: kurze zentrale Uebergaenge duerfen Navigation, Filter, Fokus, Speichern oder fachliche Signale nie verzoegern.
- Reduced Motion setzt alle Endzustaende sofort; Tabellen, Leerzustaende, globale Navigation und Dialoge bleiben bewusst statisch beziehungsweise nativ.

## 3. Primäre User Journeys

- Erste Ausführung -> Konto/Legacy-Aufnahme -> fachliche Shell ->
  Erste Schritte -> vorhandene Einrichtungseiten -> Dashboard
- Stammgruppenübersicht -> Schülerprofil -> Neue Beobachtung -> Speichern -> Schülerprofil
- Stammgruppenübersicht -> Schülerprofil -> Kompetenz -> Verlauf
- Kursübersicht -> Schülerprofil

## 4. Bildschirmübersicht

- Stammgruppenübersicht
- Kursübersicht
- Schülerprofil
- Neue Beobachtung
- Kompetenzansicht
- Erste Schritte

## 5. Stammgruppenübersicht

Primärer Zweck:

- Schüler schnell finden und auswählen.
- Anschließend in das Schülerprofil wechseln.

Elemente:

- Stammgruppe
- Schülerliste
- Kurs je Schülerkarte
- Suchmöglichkeit ohne Suchbutton

Aktionen:

- Schülerprofil öffnen
- Neue Beobachtung als Kontextaktion für den ausgewählten Schüler öffnen

Nicht enthalten:

- Kompetenzbewertungen
- Detailanalysen
- Berichte
- Statistiken
- Verwaltungsfunktionen

Produktentscheidungen:

- Die Stammgruppenübersicht ist kein Dashboard.
- Die Stammgruppenübersicht ist keine Verwaltungsansicht.
- Die Stammgruppenübersicht ist keine Analyse- oder Auswertungsseite.
- Die Standardreihenfolge der Schüler erfolgt alphabetisch nach Vorname.
- Die Suche filtert die Schülerliste automatisch während der Eingabe.
- Der Pfeil auf der Schülerkarte bildet die klickbare Fläche zum Schülerprofil.
- Das Referenzdesign nutzt ein kompaktes 4-spaltiges Raster für Stammgruppen bis mindestens 28 Schüler.
- Die Stammgruppenübersicht öffnet standardmäßig mit 140 % Zoom.
- Die Schülerkarten zeigen in dieser Ansicht den Kurs, nicht erneut die Stammgruppe.
- Die Kartenfarbe orientiert sich am Kurs und wird aus der Kurszuordnung abgeleitet.
- Schülerdaten werden nicht in der Stammgruppenübersicht verwaltet.
- Die Stammgruppenübersicht ist eine abgeleitete UI-Projektion der Schülerdaten.
- Die technische Identität eines Schülers ist `student_id`; Namen dienen nur Anzeige und Suche.
- Schüler anlegen, bearbeiten und archivieren erfolgt künftig in der Schülerverwaltung.
- Die Kontextaktion `Neue Beobachtung` übergibt nur `student_id` an den zentralen Beobachtungsdialog.
- Der Beobachtungsdialog existiert projektweit nur einmal und wird auch aus dem Schülerprofil verwendet.

## 6. Kursübersicht

Primärer Zweck:

- Schüler eines Kurses unabhängig von ihrer Stammgruppe schnell finden und auswählen.
- Anschließend in das Schülerprofil wechseln.

Elemente:

- Kurs
- Schülerliste
- Stammgruppe je Schülerkarte
- Suchmöglichkeit ohne Suchbutton

Produktentscheidungen:

- Die Kursübersicht ist im globalen Arbeitsziel `Schüler` als eigenes lokales Segment `Kurse` direkt erreichbar.
- Die Kursübersicht greift auf dieselben Schülerdaten zu wie die Stammgruppenübersicht.
- Es existieren keine doppelten Daten.
- Die Kursübersicht ist ausschließlich eine Projektion des Datenmodells.
- Die visuelle Gestaltung orientiert sich am freigegebenen Design-System.
- Ein einfacher Klick auf eine Schuelerzeile oeffnet das Profil; Enter und die sekundäre Profilaktion bleiben barrierearme Alternativen.

## 7. Schülerprofil

Primärer Zweck:

- Beobachtungen erfassen und die Kompetenzentwicklung eines einzelnen Kindes verstehen.

Elemente:

- dauerhafter Profilkopf mit Name, Stammgruppe, Kurs und aktuellem Profilbereich
- lokale Navigation `Überblick`, `Beobachtungen`, `Kompetenzen`, `Bericht`, `Dateien`
- ruhige, filterbare Beobachtungsliste
- Kompetenz-Cockpit mit Fach -> Kompetenzbereich -> Thema -> Kompetenz
- Zurück zur vorherigen Übersicht

Aktionen:

- Neue Beobachtung
- Datei hinzufügen
- bestehende seltene Profilaktionen im Kontextmenü öffnen

Produktentscheidungen:

- `Neue Beobachtung` öffnet denselben zentralen Beobachtungsdialog wie der Schnellzugriff aus der Stammgruppenübersicht.
- Das Schülerprofil wird technisch über `student_id` geöffnet. Namen dienen nur der Anzeige.
- Es gibt hoechstens eine dominante primaere Aktion; `Neue Beobachtung` bleibt in jedem lokalen Profilbereich sichtbar.
- Der aktive Profilbereich wird im Kindkontext wiederholt. Ein Refresh desselben Kindes erhaelt Reiter, Filter, Disclosure und Scrollposition; ein Kindwechsel setzt lokalen Zustand sicher zurueck.
- Beobachtungen unterscheiden Datum, Fach, Kontext, Notizvorschau, Kompetenz- und Anhangszahl ohne Ampel- oder Leistungssemantik.
- Das Kompetenz-Cockpit nutzt Einrueckung, Typografie, Abstaende und Surface-Varianten; Dokumentationsabdeckung ist keine Schulnote.
- `Passende Kompetenzen` zeigt `stage_1_3` und `cross_stage`, `Klassenstufe 4` zeigt `stage_4` und `cross_stage`, `Alle Kompetenzen` zeigt den gesamten aktiven aktuellen Zielbestand. Historische Zeilen bleiben separat sichtbar und ungefiltert.

## 8. Neue Beobachtung

Ablauf und Arbeitszonen:

1. Kind, Fach, Kontext und optionale Schnellbeobachtung
2. Kompetenzsuche, Klassenstufenfilter, Auswahl und Einzelbewertung
3. Datum, Notiz, Anhänge und dauerhaft sichtbares Speichern

Der Name des Kindes bleibt oberhalb aller drei Zonen sichtbar. Der Katalog startet fuer neue Beobachtungen geschlossen; beim Bearbeiten werden genau die betroffenen Kompetenzbereiche und Themen geoeffnet. Collapse, Fachwechsel, Suche und Klassenstufenwechsel veraendern weder Auswahl noch Bewertung. Historische beziehungsweise inaktive Kompetenzen erscheinen nur als bereits gespeicherter Edit-Bestand und werden durch Suche oder neue Auswahl nicht reaktiviert.

Validierungsfehler erscheinen als `InlineMessage` direkt vor der persistenten Aktionsleiste. Speichern bleibt primaer blau, Abbrechen sekundaer. Der Dialog ist zwischen 1100 und 1300 Pixeln als grosszuegige Arbeitsflaeche ausgelegt, bleibt bei 1180 x 760 bedienbar und erzeugt keinen horizontalen Gesamtscroll. Alle Disclosure-, Auswahl-, Bewertungs- und Speicheraktionen sind per Tastatur erreichbar; Reduced Motion setzt Endzustaende ohne Verzoegerung.

## 9. Kompetenzansicht

Elemente:

- Kompetenzstand
- Anzahl Beobachtungen
- Datum der letzten Beobachtung
- Verlauf

Die Ansicht dient dazu, die Entwicklung einer einzelnen Kompetenz nachzuvollziehen.

## 10. Navigation

```text
ERSTE AUSFÜHRUNG
  -> Erste Schritte
       -> Einstellungen / Fächer für die Dokumentation
       -> Einstellungen / Stundenplan
       -> Stammdaten
       -> Schüler
       -> Einstellungen / Datensicherung

ARBEIT
  -> Heute
  -> Schüler
       -> Stammgruppen
       -> Kursverbünde
       -> Alle Schüler
       -> Schülerprofil
            -> Beobachtungen
            -> Kompetenzen
            -> Bericht
            -> Lernentwicklungsgespräch

VERWALTUNG
  -> Stammdaten
  -> Einstellungen
```

Produktregel UI Sprint 1:

- `Heute` ist der ruhige stundenplanbasierte Arbeitsstart; technisch bleibt der Screen `dashboard`.
- Die fruehere globale `Übersicht` ist als lokale Auswahl in `Schüler` integriert.
- Beobachtungen, Kompetenzen, Berichte und Lernentwicklungsgespraeche sind kindbezogene Arbeitsbereiche und keine globalen Platzhalter.
- Eine Tabellenzeile darf ausgewaehlt werden, ohne das Profil zu oeffnen. Profilnavigation erfolgt bewusst per Doppelklick, Enter oder expliziter Aktion und immer ueber `student_id`.

Produktregel Sprint 0.2C.1:

- `Erste Schritte` ist keine neue Hauptnavigation und keine fachliche
  Einrichtungspflicht. Die Ansicht erscheint nur nach Authentifizierung und
  Shell-Aufbau, bleibt ueberspringbar und kann in den Einstellungen erneut
  geoeffnet werden.
- Der Flow legt keine fachlichen Daten an, startet keinen Import und kein
  Backup und nutzt nur vorhandene Navigationsziele.

## 11. UX-Hypothesen

- `Heute` als Arbeitsstart und `Schüler` als zentraler kindbezogener Arbeitsraum.
- Dialog für `Neue Beobachtung`.
- Darstellung der Kompetenzkarten.
- Validierung im Pilotbetrieb.

## 12. Nicht Bestandteil des ersten Prototyps

- Dashboard
- Berichte
- Gruppenbeobachtung
- KI-Unterstützung
- Analysefunktionen
- Mehrstammgruppenverwaltung
- Rollenverwaltung

## 13. Berichtswerkstatt - Finalisierung und Revisionen

Die Berichtswerkstatt verwendet eine lokale Segmentnavigation mit `Schreiben`, `Kompetenzen & Belege`, `Vorschau` und `Revisionen`. Sie ist dem Kindkontext untergeordnet, per Pfeiltasten bedienbar und keine zweite globale Navigation. Gesamttext und Fachtexte bleiben im Schreibworkspace; bewusste Kompetenz-, Beobachtungs- und Diagrammauswahl liegt getrennt im Belegworkspace. Die Zustands- und Scrollhaltung der internen Stacks bleibt bei Bereichswechseln erhalten.

Der kompakte Kopf zeigt Kind, Stammgruppe, Berichtstyp, Zeitraum, verantwortliche Lehrkraft, `Entwurf`, `Finalisiert · Revision X` oder `Entwurf geändert` sowie den letzten Finalisierungskontext. Technische `RPD`-/`RPV`-IDs und Snapshot-Hashes dominieren nicht. Eine persistente Aktionsleiste fuehrt `Entwurf speichern` als einzige primaere Draftaktion; Vorschau und Schliessen bleiben sekundaer. Finalisieren steht ausschliesslich im fachlich getrennten Revisionsbereich.

Die Vorschau ist eine dokumentartige `Vorschau des aktuellen Entwurfs`. Sie benennt, ob die dargestellten Widgetinhalte dem gespeicherten Draft entsprechen oder noch ungespeicherte Aenderungen enthalten. Der vorhandene PDF-Weg wird ausschliesslich als Entwurfs-PDF bezeichnet und nicht mit einer finalen Revision verwechselt.

Vor jeder Finalisierung wird der aktuelle Draft gespeichert und zentral validiert. Die Bestaetigung zeigt Kind, Berichtstyp, Zeitraum, ausgewaehlte Faecher sowie Kompetenz- und Beobachtungsanzahl. Der Anzeigename der verantwortlichen Lehrkraft ist verpflichtend. Eine ruhige Warnung erklaert die Unveraenderlichkeit und die Korrektur als Folgerevision; eine ausdrueckliche Bestaetigung ist erforderlich.

Das Revisionsprotokoll ist kompakt, neueste zuerst und vollstaendig lesend. Es bietet je Revision ausschliesslich `Öffnen`; Bearbeiten, Loeschen, Entsperren, Wiederherstellen und Ueberschreiben existieren nicht. Die finale Ansicht zeigt als schreibgeschuetztes historisches Dokument Kontext, Texte, Kompetenzen, Beobachtungsbelege und gespeicherte Diagrammdaten ohne editierbar wirkende Felder. Sie laedt keine aktuellen Stammdaten oder operativen Fachinhalte nach und bietet ohne revisionsgebundenes PDF-Artefakt keine PDF-Aktion.

## 14. Lernentwicklungsgespraech - Sechs-Phasen-Workspace

Der produktive LEG-Arbeitsentwurf wird als klar gefuehrter Workspace mit dauerhaftem Kind- und Gespraechskontext, kompakter linker Phasenleiste, genau einer aktiven Phase und einer persistenten unteren Aktionsleiste bearbeitet. Die Phasenleiste zeigt ausschliesslich `Aktuell`, `Inhalt vorhanden` oder `Noch leer`; sie behauptet weder Vollstaendigkeit noch Abschluss.

Die Inhaltsrollen sind verbindlich und auch ohne Farbe lesbar: `Nur für die Vorbereitung` kennzeichnet interne Lehrkrafttexte, `Im Gespräch bearbeiten` Kindrueckblick und Entwicklungsfelder, `Im Entwurf als Vereinbarung festgehalten` die weiterhin bearbeitbaren gemeinsamen Ziele, Unterstuetzungen, Vereinbarungen, Zustaendigkeiten und den optionalen Ueberpruefungstermin. `agreed_goals_text` wird sichtbar in Phase 4 bearbeitet, ohne seine bestehende Persistenzbedeutung zu aendern.

Kompetenzen, Beobachtungsbelege und optionale Gespraechsbilder werden ausschliesslich in Phase 5 ausgewaehlt. Andere Phasen zeigen dieselbe aktuelle Auswahl read-only und navigieren mit `Belege ansehen` zu Phase 5. Historische Kompetenzreferenzen und nicht mehr verfuegbare Beobachtungsreferenzen bleiben neutral sichtbar und koennen nur ausdruecklich abgewaehlt werden.

`Entwurf speichern` bleibt die einzige persistierende Hauptaktion. Zurueck, Weiter, Phasendirektwahl, Suche und Disclosure veraendern nur lokalen UI-State. Ungespeicherte Aenderungen werden zentral aus dem aktuellen Widgetstand gegen den zuletzt geladenen beziehungsweise erfolgreich gespeicherten Draft ermittelt. Escape, Fenster-Schliessen und die sichtbare Aktion `Schließen` verwenden denselben Drei-Wege-Ablauf `Entwurf speichern`, `Änderungen verwerfen`, `Weiter bearbeiten`.

Der Workspace ist fuer 1400 x 900, 1280 x 800 und 1180 x 760 ausgelegt. Kopf, Phasenleiste und Aktionsleiste bleiben erreichbar; jede aktive Phase besitzt hoechstens einen dominanten vertikalen Scrollbereich und keinen horizontalen Gesamtscroll. Phasen sind per Pfeil hoch/runter sowie Home/End bedienbar, alle Eingaben und Auswahlen besitzen Accessible Names, und Reduced Motion setzt Phasen-, Disclosure- und Feedback-Endzustaende sofort.
