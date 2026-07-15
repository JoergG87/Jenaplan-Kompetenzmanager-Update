# Schülerprofil – isolierter UX-Prototyp

## Start

Vom Projektstamm aus:

```bash
python3 prototypes/student_profile_ux/main.py
```

Der Prototyp benötigt ausschließlich `PySide6`, verwendet nur fiktive Daten aus `demo_data.py` und importiert keine produktiven Projektmodule.

## UX Discovery – Beobachtungskapitel

Die eigenständige Discovery verwirft die klassische Linien- und Zeitreihengrafik vollständig:

```bash
python3 prototypes/student_profile_ux/discovery_mockup.py
```

Der gewählte Entwurf zeigt den aktuell dokumentierten Stand und darunter ausschließlich reale Beobachtungen beziehungsweise Bestätigungen als getrennte chronologische Kapitel. Nur eine tatsächliche Änderung erhält den expliziten Zwischenblock `Dokumentierter Statuswechsel`. Es gibt keine Achse, Kurve, Interpolation oder automatische Trendinterpretation.

Die Begründung, sechs grundverschiedene Konzepte, ihre Bewertung und die Entscheidung stehen in [DISCOVERY.md](DISCOVERY.md).

Referenzscreenshots:

```bash
QT_QPA_PLATFORM=offscreen python3 prototypes/student_profile_ux/discovery_mockup.py \
  --width 1400 --height 900 \
  --screenshot prototypes/student_profile_ux/screenshots/discovery-observation-chapters-1400x900.png

QT_QPA_PLATFORM=offscreen python3 prototypes/student_profile_ux/discovery_mockup.py \
  --width 1180 --height 760 \
  --screenshot prototypes/student_profile_ux/screenshots/discovery-observation-chapters-1180x760.png
```

## Bedienung

- Oben zwischen `Variante A · empfohlen` und `Variante B` wechseln.
- Einen der neun statischen Demozustände auswählen.
- In Variante A die Orientierungskarte für bis zu drei erkennbare Kompetenzänderungen prüfen.
- Zwischen den Kompetenzkartenstudien `Ring` und `Leisten` wechseln; `Ring` ist die ruhige Standarddarstellung.
- Innerhalb der Variante A `Überblick`, `Kompetenzen`, `Beobachtungen`, `Dokumente` und `Entwicklung` öffnen. Variante B behält ihre bisherige Bezeichnung `Verlauf`.
- Kompetenzbereiche und Beobachtungsdetails aufklappen.
- Alle Aktionen zeigen ausschließlich einen flüchtigen Prototyp-Hinweis; es wird nichts gespeichert.

`Reduced Motion` ist standardmäßig aktiv. Der Prototyp verwendet unabhängig davon keine Geometrie-, Höhen- oder Screenanimationen. Alle Zustände wechseln unmittelbar.

## Varianten

### Variante A – Arbeitsprofil (empfohlen)

Ein scanbares Schülerdashboard mit horizontaler lokaler Navigation. Die erste Bildschirmhöhe priorisiert:

1. Orientierung über bis zu drei tatsächlich erkennbare Kompetenzänderungen
2. kompakte Kompetenz-/Dokumentationszahlen
3. noch nicht dokumentierte Lernbereiche
4. neueste Beobachtungen
5. Bericht, Revisionen, LEG und Dateien

Die Orientierungskarte ersetzt in Variante A das bisherige gemeinsame Kompetenz- oder Themendiagramm. Sie wählt fach- und themenübergreifend höchstens drei konkrete Kompetenzänderungen aus. Eine Kompetenz erscheint nur, wenn mindestens zwei reale Beobachtungen oder Bestätigungen vorliegen und sich der dokumentierte Status tatsächlich verändert hat. Neueste reale Statusänderungen stehen zuerst; bei gleichem Datum gilt die curriculare Reihenfolge der Demodaten.

Jede angezeigte Änderung bleibt mit ihren auslösenden beziehungsweise belegenden dokumentierten Ereignissen verknüpft. Kompetenz, früherer und neuer dokumentierter Stand sowie Zeitraum sind als Text lesbar. Die zeitliche Verbindung dient ausschließlich der Orientierung zwischen realen Ereignissen; sie stellt keinen berechneten kontinuierlichen Verlauf dar.

Kompetenzen mit nur einem Ereignis, ohne Ereignisse oder ohne Statusänderung erscheinen nicht. Die Karte erzeugt ausdrücklich keine Scores, Prozentwerte, Noten, Rankings, Mittelwerte, Lerngeschwindigkeiten oder automatische Trendinterpretationen. Mehr Beobachtungen erhöhen keinen Status. Fehlende Dokumentation erzeugt keinen negativen Status; sie bleibt in der separaten Karte `Noch nicht dokumentiert` sichtbar. Fach- und Themenchips steuern diese Übersicht nicht. Treppenlinien gehören nicht in die Übersichtsansicht.

Sind keine passenden Kompetenzen vorhanden, lautet der Zustand:

> Noch keine Entwicklung über mehrere Zeitpunkte sichtbar
>
> Sobald zu einer Kompetenz unterschiedliche dokumentierte Stände vorliegen, erscheint sie hier.

Die ausführliche Entwicklung bleibt perspektivisch Aufgabe des eigenen Tabs `Entwicklung`. `Alle Entwicklungen ansehen` zeigt im isolierten Prototyp nur Feedback und öffnet keinen produktiven Pfad.

### Variante B – Fokusprofil

Die unveränderte Vergleichsvariante reserviert mit einer schmalen lokalen Seitenleiste den Hauptbereich jeweils für eine Aufgabe. Sie verwendet weiterhin ihre bisherige einzelne statische Verlaufsgrafik.

## Demozustände

- mehrere Fächer und Themen mit mehr als drei qualifizierenden Kompetenzen
- genau drei erkennbare Entwicklungen
- fach- und themenübergreifende Entwicklungen
- wenig Dokumentation
- Berichtsentwurf vorhanden
- finalisierte Revisionen vorhanden
- LEG vorhanden
- keine Beobachtungen und damit leerer Entwicklungszustand
- historische beziehungsweise nicht verfügbare Referenz

Die Demodaten enthalten außerdem eine zwischenzeitliche Verschlechterung, unveränderte Mehrfachereignisse, eine Kompetenz mit nur einem Ereignis und eine Kompetenz ohne Ereignis. Diese Zustände prüfen die Auswahlgrenzen, erscheinen aber nicht in der Orientierungskarte.

## Screenshots erzeugen

```bash
QT_QPA_PLATFORM=offscreen python3 prototypes/student_profile_ux/main.py \
  --variant a --scenario three_developments --width 1400 --height 900 \
  --screenshot prototypes/student_profile_ux/screenshots/variant-a-recognizable-three-1400x900.png

QT_QPA_PLATFORM=offscreen python3 prototypes/student_profile_ux/main.py \
  --variant a --scenario cross_subject_developments --width 1400 --height 900 \
  --screenshot prototypes/student_profile_ux/screenshots/variant-a-recognizable-cross-subject-1400x900.png

QT_QPA_PLATFORM=offscreen python3 prototypes/student_profile_ux/main.py \
  --variant a --scenario well_documented --width 1180 --height 760 \
  --screenshot prototypes/student_profile_ux/screenshots/variant-a-recognizable-1180x760.png

QT_QPA_PLATFORM=offscreen python3 prototypes/student_profile_ux/main.py \
  --variant a --scenario no_observations --width 1180 --height 760 \
  --screenshot prototypes/student_profile_ux/screenshots/variant-a-recognizable-empty-1180x760.png
```

Bei 1400 × 900 stehen die drei Hauptkarten nebeneinander; die Orientierungskarte nutzt die vorhandene breite Spalte. Bei 1180 × 760 erhält sie zunächst die volle Inhaltsbreite, die beiden Informationskarten folgen darunter. Es gibt nur einen vertikalen Seiten-Scrollbereich und keinen horizontalen Gesamtscroll.

## Manueller Prüfblock für Laura

Die ergänzende Projektdatei `docs/laura_pilottest_feedback.csv` bündelt die Fälle `D01` bis `D28` als Prüfliste für diese UX-Referenz. Sie ersetzt nicht die führende Pilot-Testdatei `Pilottest_Laura_Schuelerprofil_Variante_A.xlsx`.

- Ist innerhalb weniger Sekunden verständlich, was sich verändert hat?
- Sind Kompetenz, früherer Stand, neuer Stand und Zeitraum klar?
- Ist die Verbindung zum dokumentierten Ereignis nachvollziehbar?
- Sind maximal drei Änderungen eine passende Menge?
- Wirkt die Karte ruhig oder weiterhin überladen?
- Sind die Einträge bei 1180 × 760 vollständig lesbar?
- Fehlt eine Information, die für die tägliche Arbeit notwendig ist?
- Wird die Darstellung fälschlich als Bewertung oder automatischer Trend verstanden?

## Abgrenzung

Der Ordner enthält keine SQLite-Verbindung, Repositorys, produktiven Adapter, produktiven ViewModels, Migration, Navigationseinbindung oder neue Fachlogik außerhalb des Prototyps. Er verändert weder Kompetenzstatusberechnung noch Bericht-/LEG-Lifecycle. Variante B ist unverändert. Der Prototyp ist eine visuelle UX-Vorlage für ein Product-Owner-Review.

Die vollständige Ist-Analyse, Rollenbewertung, Variantenentscheidung, Wireframe-Spezifikation und der vorgeschlagene spätere Umsetzungsschnitt stehen in [ANALYSIS.md](ANALYSIS.md). Die anschließende grundsätzliche Neubewertung der Visualisierungsform steht in [DISCOVERY.md](DISCOVERY.md).
