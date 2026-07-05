# Laura-Pilottest

Diese Anleitung hilft dabei, den Jenaplan-Kompetenzmanager mit kuenstlichen Testdaten im Alltag zu pruefen.

Es geht nicht um perfekte Eingaben. Wichtig ist, ob die App verstaendlich, ruhig, hilfreich und fuer paedagogische Arbeit praktikabel wirkt.

Alle Testdaten sind kuenstlich. Es werden keine echten Kindernamen und keine echten Dokumente verwendet.

## Start

Testdaten frisch erzeugen:

```bash
python3 scripts/seed_test_data.py --reset
```

App starten:

```bash
python3 -m src.desktop_app.main
```

Alternativ kann auf macOS der Launcher gestartet werden:

```text
launcher/Jenaplan_Kompetenzmanager.command
```

## Rueckmeldung eintragen

Bitte Auffaelligkeiten direkt in diese Datei eintragen:

```text
docs/laura_pilottest_feedback.csv
```

Kurz und ehrlich reicht, zum Beispiel:

- verstaendlich
- zu voll
- fehlt
- unklar
- wuerde ich anders nennen
- funktioniert nicht
- brauche ich im Alltag nicht

Status-Werte in der CSV:

- OK
- Unklar
- Fehler
- Wunsch
- Nicht getestet

Prioritaet:

- Hoch
- Mittel
- Niedrig

## A. Start & Orientierung

1. App starten.
2. Pruefen, ob Testdaten sichtbar sind.
3. Pruefen, ob Stammgruppen, Kurse und Schueler verstaendlich dargestellt sind.

Rueckmeldung:

- Findet man sich schnell zurecht?
- Wirkt die Startansicht ueberladen?
- Sind Begriffe verstaendlich?

## B. Schuelerlisten / Kursuebersichten

1. Stammgruppe oeffnen.
2. Kurs oeffnen.
3. Pruefen, ob Schueler nach Kurs und Alphabet sinnvoll sortiert sind.
4. Pruefen, ob der Dokumentationsstatus in der Liste hilfreich ist.
5. Direkt aus einer Schuelerzeile `Beobachten` oeffnen.
6. Mit `← Zur Übersicht` aus einer gefilterten Liste zur Uebersicht zurueckgehen.

Rueckmeldung:

- Reicht die Information in der Liste?
- Fehlt etwas?
- Ist der Dokumentationsstatus hilfreich oder stressig?
- Ist die Schnellaktion `Beobachten` gut auffindbar, ohne die Liste zu ueberladen?
- Ist `← Zur Übersicht` an der erwarteten Stelle?

## C. Stammdaten / Kursverbuende

1. Stammdaten oeffnen.
2. Kursverbund anschauen.
3. Neuen Kursverbund testweise anlegen.
4. Doppelte Namen testen.

Rueckmeldung:

- Ist "+ Kursverbund" verstaendlich?
- Sind Stammgruppen und Kurse logisch zuordenbar?
- Ist die Fehlermeldung bei Duplikaten verstaendlich?

## D. Schuelerprofil

Mehrere Testschueler oeffnen:

- einen gut dokumentierten Schueler
- einen teilweise dokumentierten Schueler
- einen kaum dokumentierten Schueler

Pruefen:

- Name, Stammgruppe, Kurs
- Reiter `Überblick` beim Oeffnen
- Karte `Halbjahresblick`
- Beobachtungszahl, Dokumentationsstand und letzte Beobachtung
- `Stärken` und `Im Blick behalten`
- letzte Beobachtungen als Kurzliste
- Reiter `Beobachtungen`, `Kompetenzen`, `Bericht` und `Dateien`

Rueckmeldung:

- Versteht Laura innerhalb weniger Sekunden den Lernentwicklungsstand?
- Ist die Halbjahresblick-Karte hilfreich?
- Sind Beobachtungszahl, Dokumentationsstand und letzte Beobachtung verstaendlich?
- Sind `Stärken` nachvollziehbar aus Beobachtungen und Kompetenzdaten abgeleitet?
- Ist `Im Blick behalten` hilfreich formuliert oder wirkt es defizitorientiert?
- Helfen die Reiter gegen den ersten Eindruck von Ueberladung?
- Findet Laura Beobachtungen, Kompetenzen, Bericht und Dateien weiterhin zuverlaessig?
- Geht durch die neue Struktur keine vorhandene Funktion verloren?

## E. Beobachtungen

1. Neue Beobachtung anlegen.
2. Fach auswaehlen.
3. Eine oder mehrere Kompetenzen auswaehlen.
4. Bewertung setzen.
5. Notiz eintragen.
6. Beobachtung speichern.
7. Beobachtung bearbeiten.
8. Beobachtung loeschen.
9. Neue Beobachtung direkt aus einer Schuelerliste anlegen und speichern.

Rueckmeldung:

- Ist der Dialog schnell genug?
- Sind Kompetenzauswahl und Bewertung verstaendlich?
- Ist Bearbeiten und Loeschen auffindbar?
- Ist der schnelle Einstieg aus der Liste alltagstauglich?
- Fehlt eine wichtige Beobachtungsart?

## F. Mehrfachkompetenzen / faecheruebergreifend

1. Beobachtung mit Kompetenzen aus mehreren Faechern pruefen oder neu anlegen.
2. Pruefen, ob "Faecheruebergreifend" verstaendlich angezeigt wird.

Rueckmeldung:

- Ist klar, warum dort faecheruebergreifend steht?
- Bleiben die Einzelkompetenzen trotzdem nachvollziehbar?

## G. Kompetenzvorschlaege und Entwicklung

1. Schueler mit mehreren Beobachtungen oeffnen.
2. Kompetenzuebersicht pruefen.
3. Entwicklung pruefen, zum Beispiel "- -> +".
4. Stabile Entwicklung pruefen.
5. Wechselnde Beobachtungslage pruefen.

Rueckmeldung:

- Ist der Vorschlag nachvollziehbar?
- Ist "Entwicklung" verstaendlich?
- Wirkt die Darstellung paedagogisch hilfreich?

## H. Bestaetigte Kompetenzstaende

1. Kompetenzstand bestaetigen.
2. Vorschlag uebernehmen.
3. Vorschlag bewusst abaendern.
4. Pruefen, ob die Abweichung sichtbar ist.
5. App neu starten und pruefen, ob die Bestaetigung erhalten bleibt.

Rueckmeldung:

- Ist klar, dass Laura entscheidet?
- Ist klar, was Vorschlag und was Bestaetigung ist?
- Ist die Abweichung hilfreich oder irritierend?

## I. Berichtsvorschau

Berichtsvorschau fuer mehrere Schueler oeffnen.

Pruefen:

- aktueller Stand
- Entwicklung
- Beobachtungsbelege
- bestaetigte Kompetenzstaende
- Faelle mit Einzelbeobachtung
- Faelle mit wechselnder Beobachtungslage

Rueckmeldung:

- Ist die Berichtsvorschau hilfreich?
- Welche Formulierungen sind unklar?
- Fehlt etwas fuer Elterngespraeche oder Lernentwicklung?

## J. Dokumente & Medien

1. Dokument direkt beim Schueler pruefen.
2. Dokument an Beobachtung pruefen.
3. Neues Dokument oder Medium hinzufuegen.
4. Datei oeffnen.
5. Datei entfernen.

Rueckmeldung:

- Ist "Dokumente & Medien" der richtige Begriff?
- Ist die Ablage verstaendlich?
- Braucht Laura Vorschau oder reicht Oeffnen ueber das System?

## K. Dokumentationsstand / offene Kompetenzen

1. Dokumentationsstand im Profil pruefen.
2. Details ein- und ausklappen.
3. Offene Kompetenzen pruefen.

Rueckmeldung:

- Ist das hilfreich oder wirkt es kontrollierend?
- Sollte es kompakter sein?
- Welche Ansicht braucht Laura im Alltag?

## L. Gesamteindruck

Rueckmeldung:

- Was wuerde Laura im Alltag wirklich nutzen?
- Was ist zu kompliziert?
- Was fehlt vor einem echten Einsatz?
- Welche Begriffe passen nicht?
- Welche Funktion ist am wichtigsten als naechstes?
