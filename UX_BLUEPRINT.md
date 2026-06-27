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

- Schüler auswählen.

Elemente:

- Klasse
- Schülerliste
- Such- oder Filtermöglichkeit

Aktionen:

- Schülerprofil öffnen
- Neue Beobachtung starten

Nicht enthalten:

- Kompetenzbewertungen
- Detailanalysen
- Berichte

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
