# UX Blueprint v1.0

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
- Fach -> Kompetenzbereich -> Kompetenz.
- Unterricht vor Analyse.
- Minimalistische Informationsdarstellung.

## 3. Primäre User Journeys

- Stammgruppenübersicht -> Schülerprofil -> Neue Beobachtung -> Speichern -> Schülerprofil
- Stammgruppenübersicht -> Schülerprofil -> Kompetenz -> Verlauf
- Kursübersicht -> Schülerprofil

## 4. Bildschirmübersicht

- Stammgruppenübersicht
- Kursübersicht
- Schülerprofil
- Neue Beobachtung
- Kompetenzansicht

## 5. Stammgruppenübersicht

Primärer Zweck:

- Schüler schnell finden und auswählen.
- Anschließend in das Schülerprofil wechseln.

Elemente:

- Stammgruppe
- Schülerliste
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
- Die gesamte Schülerkarte bildet die spätere Klickfläche zum Schülerprofil.
- Das Referenzdesign nutzt ein kompaktes 4-spaltiges Raster für Stammgruppen bis mindestens 28 Schüler.
- Die Stammgruppenübersicht öffnet standardmäßig mit 140 % Zoom.
- Die Kartenfarbe orientiert sich künftig am Kurs.
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

- Die Kursübersicht ist eine eigene Hauptansicht.
- Die Kursübersicht greift auf dieselben Schülerdaten zu wie die Stammgruppenübersicht.
- Es existieren keine doppelten Daten.
- Die Kursübersicht ist ausschließlich eine Projektion des Datenmodells.
- Die visuelle Gestaltung orientiert sich am freigegebenen Design-System.

## 7. Schülerprofil

Primärer Zweck:

- Beobachtungen erfassen und die Kompetenzentwicklung eines einzelnen Kindes verstehen.

Elemente:

- Name
- Stammgruppe
- Kurs
- Beobachtungsliste
- Kompetenzkarten
- Zurück zur vorherigen Übersicht

Aktionen:

- Neue Beobachtung
- Kompetenzansicht öffnen

Produktentscheidungen:

- `Neue Beobachtung` öffnet denselben zentralen Beobachtungsdialog wie der Schnellzugriff aus der Stammgruppenübersicht.
- Das Schülerprofil wird technisch über `student_id` geöffnet. Namen dienen nur der Anzeige.

## 8. Neue Beobachtung

Ablauf:

1. Notiz
2. Kompetenz(en)
3. Bewertung
4. Speichern

Die Erfassung soll schnell und klar geführt werden.

## 9. Kompetenzansicht

Elemente:

- Kompetenzstand
- Anzahl Beobachtungen
- Datum der letzten Beobachtung
- Verlauf

Die Ansicht dient dazu, die Entwicklung einer einzelnen Kompetenz nachzuvollziehen.

## 10. Navigation

```text
Stammgruppenübersicht
  -> Schülerprofil
  -> Neue Beobachtung
  -> Speichern
  -> Schülerprofil
  -> Kompetenzansicht
  -> Verlauf

Kursübersicht
  -> Schülerprofil
```

## 11. UX-Hypothesen

- Stammgruppenübersicht als Startseite.
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
