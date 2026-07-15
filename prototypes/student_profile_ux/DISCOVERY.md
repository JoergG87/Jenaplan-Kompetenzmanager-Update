# UX Discovery – Kompetenzentwicklung ohne klassische Verlaufsgrafik

Stand: 14.07.2026

Status: Entscheidungsgrundlage und isolierter UX-Mockup. Keine produktive Umsetzung.

## 1. Ausgangsthese

Eine Kompetenzentwicklung ist keine kontinuierliche Messreihe. Sichtbar sind ausschließlich einzelne pädagogische Ereignisse: eine Beobachtung oder eine bewusste Bestätigung zu einem bestimmten Datum. Zwischen diesen Ereignissen existiert kein Messwert.

Eine Liniengrafik fügt deshalb visuell etwas hinzu, das fachlich nicht vorhanden ist: Kontinuität, Steigung und eine scheinbar präzise Veränderungsgeschwindigkeit. Selbst eine technisch korrekte Treppenlinie bleibt eine grafische Interpolation und lenkt den Blick stärker auf die Form der Kurve als auf die Qualität der Belege.

Die neue Darstellung muss drei Fragen in dieser Reihenfolge beantworten:

1. Welcher Stand ist aktuell dokumentiert?
2. Durch welche realen Ereignisse ist dieser Stand entstanden?
3. Wann wurde ein anderer Stand erstmals oder erneut dokumentiert?

Sie darf keine vierte, nicht belegte Frage beantworten: Wie entwickelte sich das Kind zwischen den Ereignissen?

## 2. Bewertungsmaßstab

- Fachliche Ehrlichkeit: keine Interpolation, Durchschnitts- oder Leistungssuggestion
- Fünf-Sekunden-Orientierung für Lehrkräfte
- Rückverfolgbarkeit bis zur konkreten Beobachtung
- Lesbarkeit bei 1180 × 760 ohne horizontalen Gesamtscroll
- Umsetzbarkeit mit Standardwidgets in PySide6
- Wartbarkeit ohne spezielle Diagrammbibliothek oder QPainter-Abhängigkeit
- Skalierbarkeit von einer bis zu vielen Kompetenzen

## 3. Sechs unterschiedliche Denkmodelle

### Konzept A – Meilensteinband

**Grundidee:** Nur Ereignisse, die einen anderen Status dokumentieren, werden als beschriftete Meilensteine auf einem horizontalen Band gezeigt. Unveränderte Beobachtungen liegen als Belegzahl am jeweiligen Meilenstein.

**Vorteile:** Sehr schnelle Orientierung; Statuswechsel werden klar; deutlich weniger künstlich als eine Linie; kompakt für eine Kompetenz.

**Nachteile:** Das Band wirkt weiterhin wie eine lineare Reise mit erwarteter Richtung. Unveränderte Beobachtungen verlieren an Sichtbarkeit. Mehrere Rückwechsel können wie Rückschritt oder Scheitern erscheinen.

**Informationsdichte:** Mittel. Zeigt Statuswechsel gut, Beobachtungsqualität nur nach Drill-down.

**Alltagstauglichkeit:** Gut für einen schnellen Rückblick vor einem Gespräch, schwächer für die tägliche Belegprüfung.

**Platzbedarf bei 1180 × 760:** Eine Kompetenz benötigt etwa 170–220 Pixel Höhe. Mehrere Kompetenzen sollten nicht gleichzeitig als Bänder erscheinen.

**PySide6:** Mit `QHBoxLayout`, Karten und Labels einfach umsetzbar; keine Diagrammbibliothek nötig.

**Wartbarkeit:** Gut, solange maximal vier bis fünf Meilensteine direkt sichtbar sind.

**Viele Kompetenzen:** Mittel. Benötigt vorgelagerte Auswahl oder kompakte Liste.

**Bewertung:** 7/10.

### Konzept B – Statuswechsel-Protokoll

**Grundidee:** Eine tabellarisch ruhige Liste zeigt ausschließlich echte Wechsel als Zeilen: Datum, vorheriger Stand, neuer Stand und auslösendes Ereignis.

**Vorteile:** Höchste fachliche Präzision; keine kontinuierliche Darstellung; sehr gut sortier- und filterbar; auch viele Kompetenzen sind scanbar.

**Nachteile:** Unveränderte, aber pädagogisch wertvolle Beobachtungen verschwinden. Der Kontext einer Entwicklung wird auf Zustandswechsel reduziert. Wirkt eher administrativ als schülerzentriert.

**Informationsdichte:** Hoch, besonders fachübergreifend.

**Alltagstauglichkeit:** Gut für Kontrolle und Vorbereitung, weniger geeignet für verstehendes Lesen einer Kompetenzgeschichte.

**Platzbedarf bei 1180 × 760:** Sehr effizient; etwa sechs bis acht Zeilen sichtbar.

**PySide6:** Sehr einfach mit Standardzeilen oder `QTableView` umsetzbar.

**Wartbarkeit:** Sehr hoch; geringe visuelle Speziallogik.

**Viele Kompetenzen:** Sehr gut.

**Bewertung:** 8/10.

### Konzept C – Beobachtungskapitel

**Grundidee:** Eine Kompetenz wird als belegbasierte Geschichte aus diskreten Kapiteln gelesen. Oben steht der aktuell dokumentierte Stand. Darunter folgen reale Beobachtungen und Bestätigungen als eigenständige Karten in chronologischer Reihenfolge. Nur zwischen zwei tatsächlich unterschiedlichen Ständen erscheint ein expliziter Textblock `Dokumentierter Statuswechsel`.

**Vorteile:** Beantwortet aktuellen Stand, Entwicklung und Belege unmittelbar; jede Aussage bleibt bis zum Ereignis rückverfolgbar; keine Achse, Kurve oder Interpolation; unveränderte Beobachtungen bleiben sichtbar; Rückwechsel werden neutral dokumentiert statt bewertet.

**Nachteile:** Benötigt mehr vertikalen Raum als eine Matrix. Bei sehr vielen Ereignissen braucht es Begrenzung, Jahresgruppen oder eine vollständige Detailansicht.

**Informationsdichte:** Mittel, aber mit hoher fachlicher Aussagequalität. Details können über Disclosure verkürzt werden.

**Alltagstauglichkeit:** Sehr hoch. Lehrkräfte lesen bekannte pädagogische Einheiten: Datum, Kontext, Notiz, Status und Herkunft.

**Platzbedarf bei 1180 × 760:** In einer Detailfläche sind drei Ereignisse vollständig verständlich sichtbar. Eine linke Kompetenzliste kann bei kleiner Breite oberhalb der Kapitel erscheinen oder auf etwa 280 Pixel begrenzt bleiben.

**PySide6:** Sehr gut mit `QScrollArea`, `QVBoxLayout`, `AppCard`, `StatusBadge` und echten Buttons umsetzbar. Kein QPainter und keine Chart-Abhängigkeit.

**Wartbarkeit:** Sehr hoch, weil Darstellung und Datenmodell dieselbe Ereignisstruktur teilen. Neue Ereignisarten erweitern eine Karte statt eine Zeichenroutine.

**Viele Kompetenzen:** Gut in Kombination mit einer kompakten Kompetenzliste; immer nur eine Kompetenzgeschichte ist geöffnet.

**Bewertung:** 10/10.

### Konzept D – Kompetenzportfolio

**Grundidee:** Der aktuelle Stand steht auf einer Portfolio-Karte; darunter liegen die zwei bis drei stärksten oder neuesten Belege wie Dokumente in einer Mappe. Entwicklung entsteht durch Vergleich der Belegkarten, nicht durch eine Zeitachse.

**Vorteile:** Sehr ruhig, kindzentriert und anschlussfähig an Bericht und LEG. Beobachtungsqualität dominiert statt Statusmechanik.

**Nachteile:** Die Auswahl der „stärksten“ Belege wäre eine neue fachliche Regel. Bei rein neuesten Belegen können wichtige frühere Statuswechsel fehlen. Chronologie ist weniger deutlich.

**Informationsdichte:** Niedrig bis mittel.

**Alltagstauglichkeit:** Hoch für Gespräche und Berichte, mittel für die tägliche Verlaufsprüfung.

**Platzbedarf bei 1180 × 760:** Sehr gut; eine große Karte plus drei Belege passt problemlos.

**PySide6:** Einfach mit Standardkarten und Disclosures.

**Wartbarkeit:** Technisch hoch, fachlich nur dann hoch, wenn die Belegauswahl verbindlich definiert ist.

**Viele Kompetenzen:** Mittel; Portfolioansichten brauchen eine bewusste Auswahl.

**Bewertung:** 7/10.

### Konzept E – Beobachtungsmatrix

**Grundidee:** Kompetenzen stehen in Zeilen, Zeiträume in Spalten. Nur reale Ereignisse belegen eine Zelle mit Statuskürzel und Ereignismarker; leere Zellen bleiben leer.

**Vorteile:** Viele Kompetenzen und Zeiträume sind gleichzeitig vergleichbar. Lücken und Beobachtungsdichte werden sichtbar. Fachübergreifende Übersicht ist möglich.

**Nachteile:** Eine Matrix wirkt trotz leerer Zellen wie ein Messraster und kann regelmäßige Erhebung suggerieren. Beobachtungsnotizen verschwinden hinter Tooltips. Lehrkräfte vergleichen Zeilen leichter miteinander, obwohl kein Ranking beabsichtigt ist.

**Informationsdichte:** Sehr hoch.

**Alltagstauglichkeit:** Gut für Dokumentationskontrolle, schwächer für pädagogisches Verstehen.

**Platzbedarf bei 1180 × 760:** Kritisch bei mehr als vier Zeitspalten; interne horizontale Bewegung wäre wahrscheinlich.

**PySide6:** Mit `QTableView` gut möglich, benötigt aber sorgfältige Delegate-, Fokus- und Tooltip-Logik.

**Wartbarkeit:** Mittel; Spaltenbildung, responsive Breite und Accessibility sind aufwendiger.

**Viele Kompetenzen:** Sehr gut.

**Bewertung:** 6/10.

### Konzept F – Vorher/Heute-Snapshot

**Grundidee:** Zwei große Zustandskarten vergleichen den ersten relevanten dokumentierten Stand mit dem aktuellen Stand. Dazwischen liegen die Ereignisse als kurze Belegliste.

**Vorteile:** Aktueller Stand und Veränderung sind in Sekunden verständlich; sehr kompakt; keine Kurve.

**Nachteile:** Zwischenverläufe und Rückwechsel werden stark verkürzt. Die Wahl des „Vorher“-Zeitpunkts benötigt eine Regel und kann die Erzählung beeinflussen. Zwei Zustände wirken schnell wie Vorher-nachher-Leistungsnachweis.

**Informationsdichte:** Niedrig.

**Alltagstauglichkeit:** Gut für eine kurze Gesprächsvorbereitung, unzureichend als vollständiger Kompetenzverlauf.

**Platzbedarf bei 1180 × 760:** Sehr gering; etwa 220–280 Pixel Höhe.

**PySide6:** Sehr einfach mit Standardkarten.

**Wartbarkeit:** Technisch hoch, fachlich wegen der Snapshot-Auswahl mittel.

**Viele Kompetenzen:** Gut als Liste kompakter Paare, aber mit zunehmender Vergleichssemantik.

**Bewertung:** 6/10.

## 4. Vergleich

| Konzept | Denkmodell | Alltag | 1180 × 760 | PySide6 | Wartbarkeit | Viele Kompetenzen | Gesamt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Meilensteinband | Weg mit diskreten Stationen | gut | gut | einfach | gut | mittel | 7/10 |
| B Statuswechsel-Protokoll | fachliches Änderungsjournal | gut | sehr gut | sehr einfach | sehr hoch | sehr gut | 8/10 |
| C Beobachtungskapitel | belegbasierte Kompetenzgeschichte | sehr hoch | gut | sehr einfach | sehr hoch | gut | **10/10** |
| D Kompetenzportfolio | kuratierte Belegmappe | hoch | sehr gut | einfach | abhängig von Auswahlregel | mittel | 7/10 |
| E Beobachtungsmatrix | Ereignisraster | mittel | kritisch | mittel | mittel | sehr gut | 6/10 |
| F Vorher/Heute | Snapshotvergleich | gut | sehr gut | sehr einfach | mittel | gut | 6/10 |

## 5. Entscheidung: Beobachtungskapitel

Die klassische Grafik wird vollständig verworfen. Die beste Lösung ist eine **belegbasierte Kompetenzgeschichte aus Beobachtungskapiteln**.

Diese Entscheidung ist kein Mittelweg zwischen Diagramm und Liste. Sie setzt ein anderes fachliches Objekt ins Zentrum: nicht die gezeichnete Kurve, sondern das reale Ereignis. Der Status ist eine Eigenschaft des dokumentierten Ereignisses. Entwicklung wird ausschließlich dann sichtbar, wenn zwei Ereignisse unterschiedliche Stände tragen.

Das Konzept trennt zwei Ebenen:

- **Kompetenzübersicht:** kompakte Liste vieler Kompetenzen mit aktuellem Stand, letztem Ereignis und Beleganzahl
- **Kompetenzgeschichte:** genau eine ausgewählte Kompetenz mit allen realen Beobachtungskapiteln

Damit bleibt die Lösung auch bei vielen Kompetenzen alltagstauglich, ohne mehrere Geschichten gleichzeitig zu überlagern.

## 6. Verbindliche Mockup-Regeln

### Kopf der Kompetenzgeschichte

- Fach und Thema als Herkunft, nicht als Bewertung
- vollständige Kompetenzbezeichnung
- `Aktuell dokumentiert` mit letztem realen Status und Datum
- Anzahl realer Ereignisse
- neutraler Hinweis: `Einzelne dokumentierte Ereignisse · keine kontinuierliche Messung`

### Beobachtungskapitel

- chronologisch vom ältesten zum neuesten Ereignis
- Datum, Ereignisart, Unterrichtskontext und dokumentierter Status
- kurze Beobachtungsnotiz beziehungsweise Bestätigungsnotiz
- echte Aktion `Beobachtung öffnen` erst in einer produktiven Detailansicht
- unveränderte Beobachtungen bleiben als eigenes Kapitel sichtbar
- nur bei einer tatsächlichen Änderung erscheint zwischen zwei Karten ein neutraler Block `Dokumentierter Statuswechsel: A → B`
- keine Verbindungslinie zwischen Ereignissen
- keine Achse, Raster, Steigung, Trendfarbe oder automatisch interpretierende Sprache

### Responsive

- 1400 × 900: Kompetenzliste links, ausgewählte Geschichte rechts; drei Kapitel sind direkt lesbar
- 1180 × 760: Liste bleibt schmal, Geschichte nutzt die verbleibende Breite; genau ein vertikaler Inhalts-Scrollbereich, kein horizontaler Scroll
- unterhalb von 1100 Pixeln wäre für eine spätere Produktfassung ein Umschalten von Liste zu Detail sinnvoll; dieser Bereich liegt außerhalb der aktuellen Zielgröße

### Accessibility und Reduced Motion

- Kompetenzzeilen sind echte fokussierbare Buttons
- native Tab-Reihenfolge: Rückweg → Hauptaktion → lokale Navigation → Kompetenzliste → Ereignisse
- Status, Ereignisart und Statuswechsel stehen als Text; Farbe trägt keine alleinige Bedeutung
- Reduced Motion verändert keine Geometrie; Auswahl wechselt unmittelbar
- vollständige Ereignisinformation ist im sichtbaren Text vorhanden und nicht nur im Tooltip

## 7. Produktive Übertragung – bewusst noch nicht freigegeben

Der Mockup verwendet ausschließlich statische fiktive Daten. Eine spätere Produktfassung müsste die vorhandene kanonische Kompetenzstatus- und Evidenzprojektion über Adapter/ViewModel beziehen. Der Screen darf Status nicht neu berechnen, Ereignisse nicht gewichten und keine eigene Auswahl fachlich „wichtiger“ Belege erzeugen.

Vor einer produktiven Umsetzung sind mindestens zu entscheiden:

1. Zeigt die Kompetenzgeschichte alle Ereignisse oder zunächst eine begrenzte Anzahl mit `Alle anzeigen`?
2. Werden Bestätigungen und Beobachtungen gleichberechtigt chronologisch geführt oder visuell unterschiedlich gewichtet?
3. Wie werden korrigierte, deaktivierte oder historisch referenzierte Ereignisse gekennzeichnet?
4. Soll die Übersicht standardmäßig nach jüngstem Ereignis, curricular oder nach Fach gruppiert sein?
5. Öffnet `Beobachtung öffnen` die bestehende Beobachtungsdetailansicht oder direkt den Bearbeitungsweg?
