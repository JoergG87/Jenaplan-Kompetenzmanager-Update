# Datenmodell

Das Datenmodell wird in Version 3.1 als fachliche Grundlage vorbereitet.

Weitere Aenderungen am Datenmodell erfolgen nur nach Ruecksprache.

Das Datenmodell ist Source of Truth für fachliche Daten.

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

## Schüler, Stammgruppe und Kurs

Die bisher verwendete Bezeichnung `Klasse` wird in der Domänensprache vollständig durch `Stammgruppe` ersetzt.

Jeder Schüler gehört genau einer Stammgruppe an.

Jeder Schüler gehört genau einem Kurs an.

Der Kurs beschreibt den Jahrgang.

Die Stammgruppe beschreibt die organisatorische Zugehörigkeit.

Beides sind eigenständige fachliche Entitäten.

Beispiele für Stammgruppen:

- Grashüpfer
- Eulen
- Käfer
- Igel

Beispiele für Kurse:

- Kurs 1
- Kurs 2
- Kurs 3

### Student

Ein Student enthält mindestens:

- `student_id`
- Vorname
- Nachname
- `stammgruppe_id`
- `kurs_id`

Die `student_id` bleibt die technische Identität.

### Stammgruppe

Eine Stammgruppe enthält mindestens:

- `stammgruppe_id`
- Name

### Kurs

Ein Kurs enthält mindestens:

- `kurs_id`
- Name
- optionale Farbe für spätere UI

## Beziehungen

```text
Schüler 1:n Beobachtungen
Stammgruppe 1:n Schüler
Kurs 1:n Schüler
Beobachtung 1:n Kompetenzen
Kompetenz 1:n Kompetenzstände
Kompetenzstände 1:n Historie
```

Eine Beobachtung kann mehreren Kompetenzen zugeordnet werden.

Das ist fachlich erforderlich, weil eine Präsentation, Gruppenarbeit oder Lernzielkontrolle häufig mehrere Kompetenzen gleichzeitig sichtbar macht.

## Kompetenzstruktur ab Sprint 3A

Die sichtbare Kompetenzstruktur lautet:

```text
Fach -> Kompetenzbereich -> Thema -> Kompetenz
```

Diese Struktur nutzt vorhandene technische Felder und fuehrt keine neuen DB-Felder ein:

| Fachlicher Begriff | Bestehendes technisches Feld |
| --- | --- |
| Fach | `subject_id` / `subject_name` |
| Kompetenzbereich | `learning_area` |
| Thema | `competency_group` |
| Kompetenz | `description` / `competency_text` |
| Kurzlabel fuer kompakte UI | `label` |

Beispiel:

```text
Mathematik
  -> Groessen & Messen
    -> Zeit
      -> volle Stunden ablesen
```

Bewertungen gehoeren nicht global zur Beobachtung. Eine Beobachtung kann mehrere konkrete Kompetenzen enthalten, und jede dieser Kompetenzen traegt ihre eigene Bewertung ueber `observation_competency_ratings.rating`.

```text
Beobachtung -> Kompetenz A: +
Beobachtung -> Kompetenz B: -
Beobachtung -> Kompetenz C: ++
```

`offen` ist kein gespeicherter Ratingwert. Wenn eine Kompetenz innerhalb einer Beobachtung nicht bewertet werden soll, entsteht fuer diese Kompetenz keine Zeile in `observation_competency_ratings`.

Alte grobe Kompetenzen bleiben historisch lesbar. Bestehende Beobachtungen und bestehende `observation_competency_ratings` werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Neue konkrete Kompetenzen werden spaeter fuer neue Beobachtungen ergaenzt; alte grobe Kompetenzen duerfen spaeter deaktiviert oder archiviert werden, aber nicht geloescht werden.

Sprint 3A braucht keine Rating-Schema-Migration, weil Bewertung pro Kompetenz bereits ueber die vorhandene Zuordnungstabelle modelliert ist.

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

Die Stammgruppenübersicht ist eine abgeleitete UI-Projektion der Schülerdaten.

Sie darf keine eigene Schülerdaten-Quelle werden.

Die Projektion für die Stammgruppenübersicht enthält mindestens:

- `student_id`
- `first_name`
- `last_name`
- `display_name`
- `stammgruppe_id`
- `kurs_id`
- `status`
- `search_key`

Die sichtbaren Schülerkarten werden aus dieser Projektion abgeleitet.

Die Live-Suche arbeitet nur auf dieser abgeleiteten Projektion.

Die Kursübersicht ist ebenfalls eine abgeleitete UI-Projektion derselben Schülerdaten.

Sie zeigt alle Schüler eines Kurses unabhängig von der Stammgruppe.

Auf jeder Schülerkarte wird die Stammgruppe angezeigt.

Es existieren keine doppelten Schülerdaten für Stammgruppenübersicht und Kursübersicht.
