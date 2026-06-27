# UX Blueprint v1.0

## 1. Ziel

Der erste Prototyp dient dazu, die zentralen Arbeitsabläufe der Lehrkraft als klaren, schnellen und nachvollziehbaren Bedienfluss abzubilden.

Der Fokus liegt auf der täglichen Arbeit im Unterricht und auf der direkten Erfassung von Beobachtungen.

## 2. UX-Leitlinien

- Single Purpose Views, siehe `ADR-012` in `DECISIONS.md`.
- Beobachtung ist die fachliche Source of Truth.
- Schnellste Aktion ist `Neue Beobachtung`.
- Fach -> Kompetenzbereich -> Kompetenz.
- Unterricht vor Analyse.
- Minimalistische Informationsdarstellung.

## 3. Primäre User Journeys

- Klassenübersicht -> Schülerprofil -> Neue Beobachtung -> Speichern -> Schülerprofil
- Klassenübersicht -> Schülerprofil -> Kompetenz -> Verlauf

## 4. Bildschirmübersicht

- Klassenübersicht
- Schülerprofil
- Neue Beobachtung
- Kompetenzansicht

## 5. Klassenübersicht

Primärer Zweck:

- Schüler schnell finden und auswählen.
- Anschließend in das Schülerprofil wechseln.

Elemente:

- Klasse
- Schülerliste
- Such- oder Filtermöglichkeit

Aktionen:

- Schülerprofil öffnen

Nicht enthalten:

- Kompetenzbewertungen
- Detailanalysen
- Berichte
- Statistiken
- Verwaltungsfunktionen

Produktentscheidungen:

- Die Klassenübersicht ist kein Dashboard.
- Die Klassenübersicht ist keine Verwaltungsansicht.
- Die Klassenübersicht ist keine Analyse- oder Auswertungsseite.
- Die Standardreihenfolge der Schüler erfolgt alphabetisch nach Vorname.
- Die gesamte Schülerkarte bildet die spätere Klickfläche zum Schülerprofil.
- Das Referenzdesign nutzt ein kompaktes 4-spaltiges Raster für Klassen bis mindestens 28 Schüler.
- Schülerdaten werden nicht in der Klassenübersicht verwaltet.
- Schüler hinzufügen, bearbeiten und archivieren erfolgt künftig in der Klassenverwaltung.

## 6. Schülerprofil

Primärer Zweck:

- Beobachtungen erfassen und die Kompetenzentwicklung eines einzelnen Kindes verstehen.

Elemente:

- Name
- Klasse
- Beobachtungsliste
- Kompetenzkarten

Aktionen:

- Neue Beobachtung
- Kompetenzansicht öffnen

## 7. Neue Beobachtung

Ablauf:

1. Notiz
2. Kompetenz(en)
3. Bewertung
4. Speichern

Die Erfassung soll schnell und klar geführt werden.

## 8. Kompetenzansicht

Elemente:

- Kompetenzstand
- Anzahl Beobachtungen
- Datum der letzten Beobachtung
- Verlauf

Die Ansicht dient dazu, die Entwicklung einer einzelnen Kompetenz nachzuvollziehen.

## 9. Navigation

```text
Klassenübersicht
  -> Schülerprofil
  -> Neue Beobachtung
  -> Speichern
  -> Schülerprofil
  -> Kompetenzansicht
  -> Verlauf
```

## 10. UX-Hypothesen

- Klassenübersicht als Startseite.
- Dialog für `Neue Beobachtung`.
- Darstellung der Kompetenzkarten.
- Validierung im Pilotbetrieb.

## 11. Nicht Bestandteil des ersten Prototyps

- Dashboard
- Berichte
- Gruppenbeobachtung
- KI-Unterstützung
- Analysefunktionen
- Mehrklassenverwaltung
- Rollenverwaltung
