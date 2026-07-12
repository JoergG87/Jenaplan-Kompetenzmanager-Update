# Sprint 7D.1 – UX-Verfeinerung Lernentwicklungsgespräch (LEG)

## Start

Vom Projektstamm aus:

```bash
python3 prototypes/learning_conference_ux/main.py
```

Voraussetzung ist ausschließlich `PySide6`. Der Prototyp importiert keine produktiven Projektmodule.

## Ziel

Der Prototyp unterstützt die gemeinsame UX-Validierung der Frage:

> Worüber möchten wir im Lernentwicklungsgespräch sprechen?

Er bildet keinen Bericht ab und erzeugt keine offizielle Dokumentation. Links bereitet die Lehrkraft das Gespräch vor, rechts entsteht daraus unmittelbar eine ruhige, gesprächsgeeignete Mappe.

## Aufbau

- Linke, eigenständig scrollbare Seite: Vorbereitung und bewusste Auswahl.
- Rechte, eigenständig scrollbare Seite: live synchronisierte Gesprächsansicht.
- Dokumentkopf mit Schüler, Zeitraum, Datum und Lehrkraft.
- Getrennte Mehrfachauswahl für fachliche Bereiche und übergreifende Gesprächsthemen.
- Die gewählten Bereiche filtern unmittelbar die links sichtbaren Kompetenzgruppen und Beobachtungsbelege.
- Gruppierte Kompetenzauswahl entlang `Fach → Kompetenzbereich → Thema → konkrete Kompetenz`; alle Ebenen sind einklappbar.
- Bestätigter Stand und letzte Beobachtung bleiben interne Vorbereitung und erscheinen nicht rechts.
- Bewusste Auswahl konkreter Beobachtungsbelege mit einem Richtwert von drei bis fünf Beispielen.
- Gesprächsleitfaden mit vier frei änderbaren Demo-Textfeldern.
- Drei optional einblendbare, rein informative Darstellungen.

Die Gesprächsansicht gliedert sich in:

1. Gesprächsziel
2. Was gelingt dem Kind?
3. Welche Entwicklung sehen wir?
4. Woran möchten wir gemeinsam arbeiten?
5. Welche ausgewählten Beispiele stützen die Einschätzung?
6. Welche Unterstützung und Vereinbarungen treffen wir?

Im letzten Abschnitt werden `Vorbereitung der Lehrkraft` und `Im Gespräch vereinbart` sichtbar getrennt. Diese Trennung bildet keine Rollen-, Freigabe- oder Lifecycle-Logik ab.

## Interaktionen

Alle Änderungen links werden nach einer kurzen UI-seitigen Aktualisierungsverzögerung rechts sichtbar:

- Dokumentkopf ändern
- fachliche Bereiche auswählen
- übergreifende Gesprächsthemen auswählen
- Kompetenzen und Beobachtungsbelege passend zur Bereichsauswahl ein- und ausblenden, ohne ihre Auswahl automatisch zu löschen
- Fach-, Kompetenzbereichs- und Themenebenen ein- und ausklappen
- Kompetenzen in das Gespräch aufnehmen oder entfernen
- Beobachtungsbeispiele verwenden oder entfernen
- bei mehr als fünf Belegen einen ruhigen Hinweis anzeigen, ohne die Auswahl zu verändern
- die drei verbleibenden Diagrammtypen ein- und ausblenden
- vier Leitfadenfelder live bearbeiten

Der Zustand lebt ausschließlich in den laufenden PySide-Widgets. Nach dem Schließen ist er vollständig verworfen.

## Diagramme

- `Dokumentationsabdeckung`: zeigt ohne Prozentwert, zu welchen Gesprächsfeldern fiktive Belege vorliegen.
- `Kompetenzentwicklung`: stellt datierte Einzelstände ohne Verbindung, Richtung oder Trendinterpretation nebeneinander.
- `Zeitachse ausgewählter Beobachtungsbelege`: zeigt nur bewusst ausgewählte Beispiele in chronologischer Reihenfolge.

Die Diagramme sind keine Leistungsbewertung. Sie enthalten keine Noten, Durchschnittswerte, Scores oder automatisch behaupteten Trends.

## Fiktive Demo-Daten

- Kind: `Mara Beispielkind`
- Lehrkraft: `Laura Musterlehrerin`
- Stammgruppe: `Sonnenbogen`
- Zeitraum: `Februar bis Juli 2026`
- Fachliche Bereiche: Deutsch, Mathematik, EPU und Kunst
- Übergreifende Gesprächsthemen: Arbeitsverhalten, Sozialverhalten, Selbstständigkeit und Lernorganisation
- Mathematik-Zeitkompetenzen: volle Stunde, halbe Stunde, Viertelstunde, minutengenau, einstellen, notieren und Schreibweisen übertragen
- Ausschließlich erfundene Beobachtungen, Stände, Gesprächsziele und Vereinbarungen

Die Demo-Daten liegen gebündelt in `demo_data.py` und werden beim Start in den Arbeitsspeicher geladen.

## Bewusste Abgrenzung

Dieser Ordner ist vollständig isoliert und später als Einheit entfernbar. Es gibt ausdrücklich:

- keine Änderung und keinen Import der produktiven App
- keine SQLite-Verbindung oder andere Persistenz
- keine Repositorys, Adapter oder ViewModels
- keine Migration und keine Datenmodelländerung
- keine Berichtserzeugung, PDF-Erzeugung, LEG-Persistenz, Speicherung, Freigabe oder Produktintegration
- keine Änderungen an Governance-Dokumenten
- keine fachliche Auswertungslogik
- keine Tests für den Prototyp

Die Texte in der rechten Ansicht sind eine flüchtige Gesprächsprojektion. Ziele, Vereinbarungen und Gesprächsergebnisse werden nicht zu Fachdaten.

## Dateien

- `main.py`: isolierte PySide6-Oberfläche, Demo-Interaktionen und Live-Projektion
- `demo_data.py`: ausschließlich fiktive In-Memory-Daten
- `README.md`: Start, Umfang, Diagrammsemantik und Abgrenzung

## Offene Product-Owner-Fragen für das UX-Review

1. Soll der Dokumentkopf in einer späteren Produktfassung editierbar sein oder vollständig aus dem Schüler- und Terminkontext kommen?
2. Soll eine abgewählte Fach- oder Themenauswahl nur rechts ausblenden oder links zusätzlich die Belegauswahl filtern?
3. Wie viele ausgewählte Kompetenzen bleiben neben drei bis fünf Beobachtungsbelegen im realen Gespräch gut erfassbar?
4. Unterstützen alle drei verbliebenen Darstellungen das Gespräch oder soll die Gesprächsmappe standardmäßig ganz ohne Diagramm starten?
5. Soll der gemeinsam vereinbarte Teil während des Gesprächs im selben Arbeitsbereich editierbar werden oder in einer späteren eigenen Gesprächsphase?
6. Welche Beteiligung des Kindes und der Sorgeberechtigten soll eine spätere Gesprächsansicht sichtbar unterstützen?
7. Falls Vereinbarungen später gespeichert werden: Wann gelten sie als gemeinsam vereinbart, wer darf sie ändern und wie wird ihre Historie geschützt?
