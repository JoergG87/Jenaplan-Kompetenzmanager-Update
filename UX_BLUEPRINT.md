# UX Blueprint v1.0

## Version 0.2.0 - Release- und Sicherheitskommunikation

Handbuch, Handouts, Release-Screenshots und Laura-Übergabe verwenden dieselben
ruhigen Primärtexte wie die App. `Auf diesem Gerät angemeldet bleiben` wird nie
als dauerhafte Sitzung beschrieben; Inaktivitäts- und Wake-Sperre bleiben
sichtbar. Touch ID ist optional, das Passwort bleibt Fallback. Die verbindliche
Grenze lautet: `Die App-Sperre ist keine Verschlüsselung der Datenbank,
Dokumente oder Backups.`

Der Support-Reset-Einstieg bleibt sichtbar, kennzeichnet die fehlende produktive
Freischaltung jedoch vor einer Tokenaktion. Screenshots zeigen ausschließlich
neutrale künstliche oder leere Zustände und niemals Passwörter, Recovery-Codes,
Tokens, Schülerdaten oder lokale Pfade. Offene physische Prüfungen werden nicht
durch Offscreen-Aufnahmen ersetzt.

## Support-Reset - ruhiger Recovery-Handoff

Der Einstieg heißt `Weitere Wiederherstellungsmöglichkeiten` im Auth-Gate und
`Technische Support-Reset-Anfrage erstellen` im bestehenden Bereich
`Einstellungen > Sicherheit > Wiederherstellung`. Es entsteht weder eine neue
Hauptnavigation noch ein prominenter Supportpfad während normaler Facharbeit.

Der modale Ablauf besitzt klar getrennte Zustände: Erklärung, Anfrage,
Reset-Code, geprüfte Vorschau und laufender Abschluss. Kopieren und Dateiexport
erfolgen ausschließlich nach expliziter Aktion. Token und Signatur werden nie
automatisch in Zwischenablage, Preferences oder Datei übernommen.

Nach gültiger Prüfung nennt die Vorschau ruhig die Folgen und bietet genau die
Primäraktion `Sicherheitsbackup erstellen und Passwort zurücksetzen`. Escape und
Schließen führen nie zum Reset. Während Backup und Commit zeigt die Oberfläche
einen unbestimmten Fortschritt, verhindert Mehrfachauslösung und wartet auf das
echte Workerende. Bei erfolgreichem Commit gibt es kein Zurück zur Fach-UI.

Eine leere produktive Key Registry wird nicht als technischer Defekt inszeniert,
sondern mit dem verbindlichen Satz erklärt: `Der Support-Reset ist in dieser
App-Version noch nicht für den produktiven Betrieb freigeschaltet.`

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

## 2.1 Fachorientierung im Qt-Pilot

Fachnamen bleiben in jedem Fachkontext sichtbar. Ein kleiner zentraler Marker
unterstützt lediglich das schnelle Wiedererkennen: Deutsch Rot, Mathematik
Blau, Englisch Schwarz, Musik Gelb, Ethik und Religion Orange sowie
Schulgarten Braun. EPU/Sachkunde, Kreatives Gestalten, Selbst- und
Sozialkompetenz, Arbeits-/Lernkompetenz und unbekannte Fächer bleiben
neutral. Kreatives Gestalten wird nicht mit Werken gleichgesetzt.

Dashboard, Stundenplan, Beobachtungsdialog, Schülerprofil, Fachübersicht,
Kompetenz-Cockpit, Bericht und LEG verwenden dieselbe zentrale Auflösung aus
der stabilen Fach-ID. Weitere beziehungsweise individuell gewählte Fächer
ändern ihre Farbe nicht durch die Position in der Auswahl. Kursfarbe,
Bewertungsfarbe und Statusfarbe bleiben getrennte visuelle Rollen. Marker
werden nicht auf jede untergeordnete Kompetenzzeile wiederholt, färben keine
ganzen Karten oder Dokumentflächen und besitzen keinen eigenen Tabstop.

Ein- und ausklappbare Fach- und Beobachtungskarten setzen ihren Zustand sofort
und ohne geometrieverändernden Hovereffekt. Dynamische Fachübersichten
reservieren die Höhe ihrer vollständigen Zeilen. Lange Bericht-Fachlisten
scrollen unabhängig von der dauerhaft erreichbaren Weiter-Aktion. Mehrzeilige
Statusmeldungen wachsen anhand ihrer tatsächlichen Rahmen- und Inhaltsbreite,
damit keine Textzeile abgeschnitten wird.

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
       -> Stammdaten
       -> Schüler
       -> Einstellungen / Stundenplan
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
- Der Final-V4-Pilotflow führt in fünf nicht blockierenden Schritten von
  lokalem Schutz und Recovery-Codes über die vorbereitete Arbeitsgrundlage zu
  Stammdaten, kindbezogener Unterrichtsfachauswahl, erster Beobachtung und
  `.jkmebackup`. Die globale Dokumentationsfachauswahl ist keine
  Startvoraussetzung.
- Die kindbezogene Bedienung läuft über `Schüler` -> `Profil öffnen` ->
  `Überblick` -> `Fächer für die Dokumentation` -> `Aufklappen`. Die Auswahl
  umfasst nur Unterrichtsfächer und priorisiert den normalen
  Dokumentationsworkflow; überfachliche Entwicklung bleibt unabhängig davon
  verfügbar, weitere aktive Unterrichtsfächer bleiben in Beobachtung unter
  `Weitere Fächer` erreichbar.

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

Die Berichtswerkstatt verwendet für den Pilot eine lokale Segmentnavigation mit
`Auswählen`, `Schreiben` und `Prüfen & finalisieren`. Sie ist dem Kindkontext
untergeordnet, per Pfeiltasten bedienbar und keine zweite globale Navigation.
Ein neuer Entwurf beginnt bei `Auswählen`, ein vorhandener Entwurf bei
`Schreiben`; beide Bereiche bleiben jederzeit direkt erreichbar und bilden
keinen starren Assistenten. Gesamttext und Fachtexte bleiben im
Schreibworkspace, die bewusste Kompetenz-, Beobachtungs- und Diagrammauswahl im
Auswahlworkspace. Die internen Routen und die Zustands- und Scrollhaltung der
vorhandenen Stacks bleiben bei Bereichswechseln erhalten.

Der kompakte Kopf zeigt Kind, Stammgruppe, Berichtstyp, Zeitraum, verantwortliche Lehrkraft, `Entwurf`, `Finalisiert · Revision X` oder `Entwurf geändert` sowie den letzten Finalisierungskontext. Technische `RPD`-/`RPV`-IDs und Snapshot-Hashes dominieren nicht. Eine persistente Aktionsleiste fuehrt `Entwurf speichern` als einzige primaere Draftaktion; Vorschau und Schliessen bleiben sekundaer. Finalisieren steht ausschliesslich im fachlich getrennten Revisionsbereich.

Die Vorschau ist die zentrale dokumentartige Prüffläche innerhalb von
`Prüfen & finalisieren`. Sie benennt, ob die dargestellten Widgetinhalte dem
gespeicherten Draft entsprechen oder noch ungespeicherte Aenderungen enthalten.
Von dort bleiben die vorhandene Finalisierung und `Frühere Fassungen`
erreichbar. Der vorhandene PDF-Weg wird ausschliesslich als Entwurfs-PDF
bezeichnet und nicht mit einer finalen Revision verwechselt.

Vor jeder Finalisierung wird der aktuelle Draft gespeichert und zentral validiert. Die Bestaetigung zeigt Kind, Berichtstyp, Zeitraum, ausgewaehlte Faecher sowie Kompetenz- und Beobachtungsanzahl. Der Anzeigename der verantwortlichen Lehrkraft ist verpflichtend. Eine ruhige Warnung erklaert die Unveraenderlichkeit und die Korrektur als Folgerevision; eine ausdrueckliche Bestaetigung ist erforderlich.

Das sekundär als `Frühere Fassungen` erreichbare Revisionsprotokoll ist
kompakt, neueste zuerst und vollstaendig lesend. Es bietet je Revision
ausschliesslich `Öffnen`; Bearbeiten, Loeschen, Entsperren, Wiederherstellen und
Ueberschreiben existieren nicht. Die finale Ansicht zeigt als
schreibgeschuetztes historisches Dokument Kontext, Texte, Kompetenzen,
Beobachtungsbelege und gespeicherte Diagrammdaten ohne editierbar wirkende
Felder. Sie laedt keine aktuellen Stammdaten oder operativen Fachinhalte nach
und bietet ohne revisionsgebundenes PDF-Artefakt keine PDF-Aktion.

Ungespeicherte Änderungen verwenden über sichtbares Schließen, Escape und
Fensterschließen denselben Drei-Wege-Dialog `Entwurf speichern`, `Änderungen
verwerfen`, `Weiter bearbeiten`. Weiterbearbeiten ist Standard- und
Escape-Aktion; Verwerfen ist niemals Default. Nach der Speicherwahl schließt
die Werkstatt erst nach bestätigt erfolgreichem RPD-Speichern.

## 14. Lernentwicklungsgespraech - drei Arbeitskontexte

Der produktive LEG-Arbeitsentwurf ordnet sechs fachliche Anker in drei
verstaendliche Arbeitskontexte: `Vorbereitung`, `Im Gespräch` sowie
`Vereinbarungen & Abschluss`. Die Navigation zeigt den aktuellen Kontext und
vorhandenen Inhalt, behauptet aber weder Vollstaendigkeit noch Abschluss.

Die sechs Anker sind `Gesprächsziel`, `Was gelingt dem Kind?`, `Welche
Entwicklung sehen wir?`, `Woran möchten wir gemeinsam arbeiten?`, `Welche
Beispiele stützen unsere Einschätzung?` sowie `Welche Unterstützung und
Vereinbarungen treffen wir?`. Ihre Rollen bleiben auch ohne Farbe lesbar:
interne Vorbereitungstexte, im Gespraech bearbeitete Rueckblicke und
Entwicklungsfelder sowie weiterhin bearbeitbare gemeinsame Ziele,
Unterstuetzungen, Vereinbarungen, Zustaendigkeiten und der optionale
Ueberpruefungstermin.

Kompetenzen, Beobachtungsbelege und optionale Gespraechsbilder werden primaer
in der Vorbereitung ausgewaehlt und koennen im Gespraech bei Bedarf erreicht
werden. Der kanonische Kompetenzstand bleibt read-only; ausserhalb des
Belegankers erscheint die aktuelle Auswahl als read-only Zusammenfassung.
Historische Kompetenzreferenzen und nicht mehr verfuegbare
Beobachtungsreferenzen bleiben neutral sichtbar. Es entsteht keine eigene
LEG-Bewertung.

`Entwurf speichern` bleibt die einzige persistierende Hauptaktion. Kontextwahl,
Suche und Disclosure veraendern nur lokalen UI-State. Ungespeicherte
Aenderungen werden gegen den zuletzt geladenen beziehungsweise erfolgreich
gespeicherten Draft ermittelt. Escape, Fenster-Schliessen und die sichtbare
Aktion `Schließen` verwenden denselben Drei-Wege-Ablauf `Entwurf speichern`,
`Änderungen verwerfen`, `Weiter bearbeiten`.

Der Workspace ist fuer 1400 x 900, 1280 x 800 und 1180 x 760 ausgelegt. Kopf,
Kontextnavigation und Aktionsleiste bleiben erreichbar; jeder Kontext besitzt
hoechstens einen dominanten vertikalen Scrollbereich und keinen horizontalen
Gesamtscroll. Alle Eingaben und Auswahlen besitzen Accessible Names, und
Reduced Motion setzt Navigations-, Disclosure- und Feedback-Endzustaende
sofort.
