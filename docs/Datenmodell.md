# Datenmodell

Das Datenmodell wird in Version 3.1 als fachliche Grundlage vorbereitet.

Weitere Aenderungen am Datenmodell erfolgen nur nach Ruecksprache.

## Erkenntnisse aus dem Discovery-Workshop

Der erste Discovery-Workshop mit einer erfahrenen Jenaplan-Grundschullehrkraft hat das fachliche Verständnis des Kompetenzmanagers geschärft.

Der Kompetenzmanager wird fachlich als Lernentwicklungsmanager verstanden.

Die zentrale fachliche Entität ist die Beobachtung.

Nicht die Bewertung.

Bewertungen sind Ergebnisse dokumentierter Beobachtungen und dürfen nicht als alleinige Quelle der Lernentwicklung verstanden werden.

## Fachliche Kernobjekte

Die fachlichen Kernobjekte stehen in folgender Beziehung:

```text
Schüler
  ↓
Beobachtung
  ↓
Kompetenz
  ↓
Kompetenzstand
  ↓
Berichte / Dashboard
```

Die Beobachtung ist die zentrale fachliche Entität.

Nicht die Bewertung.

Aus Beobachtungen werden Kompetenzstände, Schülerprofile, Lernentwicklungsberichte, Dashboards und Auswertungen abgeleitet.

## Schüleridentität

Die technische Identität eines Schülers ist immer `student_id`.

Namen dienen ausschließlich der Anzeige und Suche.

Vorname, Nachname oder Anzeigename dürfen nicht als technische Identität verwendet werden.

## Beziehungen

```text
Schüler 1:n Beobachtungen
Beobachtung 1:n Kompetenzen
Kompetenz 1:n Kompetenzstände
Kompetenzstände 1:n Historie
```

Eine Beobachtung kann mehreren Kompetenzen zugeordnet werden.

Das ist fachlich erforderlich, weil eine Präsentation, Gruppenarbeit oder Lernzielkontrolle häufig mehrere Kompetenzen gleichzeitig sichtbar macht.

## Beobachtung

Eine Beobachtung beschreibt eine fachlich relevante Wahrnehmung im Lernprozess eines Kindes.

Typische Entstehungssituationen sind:

- Lernzielkontrolle
- Präsentation
- Einzelgespräch
- Gruppenarbeit
- Leseübung
- Unterrichtsbeobachtung

Diese Situationen bilden später den Beobachtungskontext.

Der Beobachtungskontext hilft, Kompetenzstände nachvollziehbar und pädagogisch begründet abzuleiten.

## Kompetenzentwicklung

Kompetenzentwicklung entsteht über einen längeren Zeitraum.

Der aktuelle Stand reicht fachlich nicht aus.

Das Datenmodell muss deshalb historisierte Kompetenzstände unterstützen.

Frühere Entwicklungsstände werden nicht überschrieben, sondern bleiben als Verlauf nachvollziehbar.

## Erweitertes fachliches Modell

Die Discovery Phase 1 erweitert das fachliche Modell um den Unterrichtskontext:

```text
Unterricht
  ↓
Situation
  ↓
Beobachtung
  ↓
Kompetenzentwicklung
  ↓
Festgestellter Kompetenzstand
```

Der Kompetenzstand ist eine pädagogische Feststellung.

Nicht das unmittelbare Ergebnis einer einzelnen Beobachtung.

Kompetenzentwicklung entsteht aus vielen Beobachtungen über einen längeren Zeitraum.

Die Software darf Kompetenzstände fachlich vorbereiten oder vorschlagen.

Die endgültige Feststellung verbleibt bei der Lehrkraft.

## Abgeleitete UI-Projektionen

UI-Tabellen, Hilfstabellen, Schattentabellen, Formeln und Karten sind ausschließlich abgeleitete Sichten auf das Datenmodell.

Sie dürfen niemals Source of Truth werden.

Die Klassenübersicht ist eine abgeleitete UI-Projektion der Schülerdaten.

Sie darf keine eigene Schülerdaten-Quelle werden.

Die Projektion für die Klassenübersicht enthält mindestens:

- `student_id`
- `first_name`
- `last_name`
- `display_name`
- `class_id`
- `status`
- `search_key`

Die sichtbaren Schülerkarten werden aus dieser Projektion abgeleitet.

Die Live-Suche arbeitet nur auf dieser abgeleiteten Projektion.
