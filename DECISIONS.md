# Architekturentscheidungen

## ADR-001

Excel-Dateien werden ausschließlich durch Python erzeugt.

Keine manuellen Änderungen.

## ADR-002

Es werden keine Makros und kein VBA verwendet.

## ADR-003

Apple Numbers wird vollständig unterstützt.

## ADR-004

Die Projektentwicklung erfolgt sprintbasiert.

## ADR-005

Das Bewertungssystem besteht aus:

- `++`
- `+`
- `-`

Die Darstellung erfolgt später über Ampelfarben.

## ADR-006

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs.

## ADR-007

Produktentscheidung.

Die Excel-Arbeitsmappe stellt die Benutzeroberfläche dar.

Die interne Datenstruktur darf technisch aufgebaut sein.

Die sichtbaren Arbeitsblätter orientieren sich ausschließlich an den Arbeitsabläufen der Lehrkraft.

## ADR-008

Produktentscheidung.

Die Klassenmatrix bildet zukünftig die zentrale Arbeitsansicht.

Bewertungen werden möglichst nur einmal erfasst.

Weitere Ansichten werden automatisch daraus erzeugt.

## ADR-009

Produktentscheidung.

Kompetenzen werden hierarchisch gespeichert.

Beispiel:

- Fach
- Lernbereich
- Kompetenzgruppe
- Kompetenz

## ADR-010

Produktentscheidung.

Das Datenmodell soll eine Entwicklungsdokumentation ermöglichen.

Mehrere Beobachtungen einer Kompetenz über einen längeren Zeitraum müssen zukünftig möglich sein.

## ADR-011

Produktentscheidung.

Die Software soll pädagogische Prozesse unterstützen.

Neue Funktionen werden danach bewertet, ob sie den Arbeitsalltag einer Lehrkraft vereinfachen.
