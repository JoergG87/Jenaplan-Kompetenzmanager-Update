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
