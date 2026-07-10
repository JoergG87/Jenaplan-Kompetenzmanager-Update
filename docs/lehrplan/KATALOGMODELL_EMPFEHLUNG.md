# Katalogmodell-Empfehlung Sprint 4A

Status: Architektur- und Datenmodellvorschlag. Keine CSV-Aenderung, keine SQLite-Aenderung, keine Migration, keine Code-Aenderung.

## Ausgangslage

Der aktuelle CSV-Katalog `data/curriculum_catalog_v1.csv` enthaelt 212 aktive Kompetenzzeilen in 11 Faechern. Alle Zeilen nutzen aktuell `grade_band = 1-4`.

SQLite speichert im heutigen Feldsatz der Tabelle `competencies` nur die operative Kernprojektion:

```text
competency_id
subject_id
subject_name
label
description
learning_area
competency_group
sort_order
active
is_core_subject
```

Der bestehende Katalogimport ist idempotent. Neue CSV-IDs werden eingefuegt, vorhandene IDs werden fachlich aktualisiert, aber `competencies.active` vorhandener IDs wird nicht aus der CSV ueberschrieben. Dieser Bestandsschutz ist fachlich richtig und soll erhalten bleiben.

## Fachliches Zielmodell

Der Kompetenzkatalog bleibt ein beobachtbarer, bewertbarer Fachkatalog:

```text
Fach -> Kompetenzbereich -> Thema -> Kompetenz
```

Eine Katalogzeile ist genau dann eine bewertbare Kompetenz, wenn sie in einer konkreten Unterrichtssituation unabhaengig beobachtet und mit `++`, `+`, `-` oder `--` bewertet werden kann.

Historische Katalogeintraege bleiben ueber ihre `competency_id` lesbar. Neue fachliche Praezision entsteht durch neue stabile Kompetenz-IDs, nicht durch Umdeutung bestehender IDs.

## Empfohlene dauerhafte CSV-Struktur

Die CSV sollte dauerhaft folgende Spalten fuehren:

| Spalte | Zweck |
| --- | --- |
| `competency_id` | stabile technische Kompetenz-ID, Primaerschluessel des Katalogs |
| `subject_key` | stabiler technischer Fachschluessel, spaeter `subject_id` in SQLite |
| `subject_display_name` | kurzer App-Anzeigename des Fachs |
| `subject_full_name` | voller schulischer Fachname |
| `official_subject_name` | offizieller Quellen- oder Lehrplanname |
| `school_context_name` | schulischer Kontext, z. B. Jenaplan- oder Projektunterrichtsbezug |
| `grade_band` | quellenbezogener Geltungsbereich, z. B. `1-4` |
| `learning_stage` | produktbezogene Filterstufe fuer die App |
| `learning_area` | Kompetenzbereich |
| `competency_group` | Thema innerhalb des Kompetenzbereichs |
| `competency_text` | konkrete beobachtbare Kompetenz |
| `competency_label` | kompaktes UI-Label |
| `source_reference` | knapper Quellen- oder Arbeitskatalogverweis |
| `catalog_status` | fachlicher Katalogstatus |
| `is_core_subject` | Kernfach-/Standardfach-Kennzeichen |
| `is_active` | Default-Aktivitaet beim Erstimport |
| `activation_group_key` | optionaler Aktivierungsbereich, z. B. fuer optionale Sportbereiche |

`catalog_status` wird empfohlen, damit Bestandsschutz, fachliche Freigabe und spaetere Archivierung nicht allein ueber `is_active` ausgedrueckt werden muessen.

Empfohlener Wertebereich:

```text
current
legacy
```

`activation_group_key` bleibt leer, wenn keine gesonderte Aktivierungslogik benoetigt wird. Fuer optionale Sportbereiche kann spaeter ein stabiler Key genutzt werden, z. B.:

```text
sport_ski_ice_inline
```

## `grade_band` reicht fachlich nicht aus

`grade_band` beschreibt den quellenbezogenen Geltungsbereich einer Kompetenz. Im aktuellen Katalog ist das durchgaengig `1-4`.

Die Product-Owner-Entscheidung zur spaeteren UI verlangt dagegen ein produktbezogenes Filtermodell:

```text
Klassenstufe 1-3
Klassenstufe 4
stufenuebergreifend
```

Diese Logik darf nicht in `grade_band` versteckt werden, weil sonst Quelleninformation und Produktfilter vermischt werden.

## Empfohlenes neues Feld

Name: `learning_stage`

Wertebereich:

```text
stage_1_3
stage_4
cross_stage
```

UI-Anzeige:

```text
stage_1_3 -> Klassenstufe 1-3
stage_4 -> Klassenstufe 4
cross_stage -> stufenuebergreifend
```

Zweck:

- Standardfilter `Passende Kompetenzen` ableiten
- Filter `Klassenstufe 1-3`, `Klassenstufe 4` und `Alle Kompetenzen anzeigen` ermoeglichen
- jahrgangsgemischte Gruppen unterstuetzen, ohne Kompetenzen zu sperren
- Berichte, Dashboard und Schuelerprofil nach fachlicher Passung vorsortieren

Auswirkungen:

- CSV braucht eine neue Spalte `learning_stage`.
- SQLite braucht spaeter eine neue persistente Spalte `learning_stage`.
- `grade_band` bleibt erhalten und wird nicht fuer UI-Filter missbraucht.
- Beobachtungen werden nicht migriert.
- Alte Kompetenzen koennen `cross_stage` erhalten, sofern keine fachliche Trennung entschieden wird.

## Dauerhaft in SQLite zu speichern

SQLite ist die produktive lokale Source of Truth. Nach dem Import muss SQLite alle Informationen enthalten, die die App ohne erneutes CSV-Lesen fuer UI, Berichte, Dokumentationsstand, Schuelerprofil und Dashboard braucht.

Empfohlene zukuenftige Struktur fuer `competencies`:

```text
competency_id TEXT PRIMARY KEY
subject_id TEXT NOT NULL
subject_name TEXT NOT NULL
subject_full_name TEXT NOT NULL DEFAULT ''
official_subject_name TEXT NOT NULL DEFAULT ''
school_context_name TEXT NOT NULL DEFAULT ''
label TEXT NOT NULL
description TEXT NOT NULL
grade_band TEXT NOT NULL DEFAULT ''
learning_stage TEXT NOT NULL DEFAULT 'cross_stage'
learning_area TEXT NOT NULL
competency_group TEXT
source_reference TEXT NOT NULL DEFAULT ''
catalog_status TEXT NOT NULL DEFAULT 'current'
activation_group_key TEXT NOT NULL DEFAULT ''
sort_order INTEGER NOT NULL DEFAULT 0
active INTEGER NOT NULL CHECK (active IN (0, 1))
catalog_default_active INTEGER NOT NULL CHECK (catalog_default_active IN (0, 1)) DEFAULT 1
is_core_subject INTEGER NOT NULL CHECK (is_core_subject IN (0, 1)) DEFAULT 1
```

`active` bleibt die lokale Arbeitsaktivitaet. `catalog_default_active` speichert den CSV-Default und darf lokale Aktivierungen nicht ueberschreiben.

Optional fuer einen spaeteren Einstellungssprint:

```text
competency_activation_groups(
  activation_group_key TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  active INTEGER NOT NULL CHECK (active IN (0, 1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
)
```

Diese optionale Tabelle ist nur noetig, wenn optionale Sportbereiche oder spaeter andere optionale Bereiche nicht einzeln pro Kompetenz, sondern als Gruppe aktiviert werden sollen.

## Ausschliesslich in der CSV zu belassen

Nicht dauerhaft in SQLite gehoeren:

- ausfuehrliche Mapping-Begruendungen
- PO-Pruefnotizen
- Quellenkommentare, die keine App-Anzeige oder Berichtsausgabe benoetigen
- Zwischenstaende der fachlichen Konsolidierung
- Rohdaten aus Lehrplan-Extraktion
- technische Import-Hilfsspalten ohne App-Bedeutung

Die CSV bleibt Seed- und Pflegeformat. SQLite bleibt nach dem Import die operative Datenbasis.

## Auswirkungen auf Upsert

Der idempotente Upsert soll erhalten bleiben:

- neue `competency_id`s einfuegen
- vorhandene fachliche Text-, Hierarchie-, Quellen- und Filterfelder aktualisieren
- lokale Nicht-CSV-Kompetenzen nicht loeschen
- bestehende Beobachtungen und bestaetigte Kompetenzstaende nicht migrieren
- `active` vorhandener IDs nicht automatisch aus der CSV ueberschreiben
- `catalog_default_active` aus der CSV aktualisieren

Fuer bestehende Datensaetze gilt:

```text
active = active
catalog_default_active = excluded.catalog_default_active
learning_stage = excluded.learning_stage
catalog_status = excluded.catalog_status
```

Damit bleiben lokale Aktivierungsentscheidungen erhalten, waehrend fachliche Katalogmetadaten nachgezogen werden.

## Auswirkungen auf Bestandsschutz

Bestandsschutz bleibt Kernregel:

- `competency_id` wird nie fachlich umgedeutet.
- Alte grobe Kompetenzen bleiben lesbar.
- Alte Kompetenzen werden nicht geloescht.
- Spaetere Deaktivierung oder Archivierung alter Eintraege braucht eine eigene PO-Freigabe.
- Historische Beobachtungen und bestaetigte Kompetenzstaende bleiben ueber bestehende IDs gueltig.

`catalog_status = legacy` kann spaeter anzeigen, dass eine Kompetenz fachlich historisch ist. Das ersetzt keine Migration und loescht keine Daten.

## Auswirkungen auf Beobachtungen

Keine unmittelbare Aenderung.

`observation_competency_ratings` speichert weiterhin die konkrete Bewertung je `observation_id` und `competency_id` sowie den beobachtungsnahen Anzeigesnapshot.

`learning_stage`, `catalog_status` und `activation_group_key` gehoeren nicht in die Beobachtung. Sie werden aus dem aktuellen Katalog gelesen, wenn neue Beobachtungen gefiltert oder historische Ansichten erklaert werden.

## Auswirkungen auf Berichte

Berichte profitieren von persistenten Katalogmetadaten:

- Fachnamen koennen kurz, vollstaendig oder offiziell angezeigt werden.
- `learning_stage` ermoeglicht alters- und kursnahe Berichtsauswahl.
- `catalog_status` verhindert, dass historische Kompetenzen unkommentiert wie aktuelle Zielkompetenzen wirken.
- Nicht aktive oder optionale Bereiche koennen im Bericht bewusst ausgeblendet oder als historisch sichtbar gehalten werden.

Berichte duerfen keine neue fachliche Datenquelle werden. Sie bleiben Projektionen aus SQLite.

## Auswirkungen auf UI

Die spaetere UI sollte filtern, nicht sperren:

- Standard: `Passende Kompetenzen`
- Filter: `Klassenstufe 1-3`
- Filter: `Klassenstufe 4`
- Option: `Alle Kompetenzen anzeigen`

Optionale Sportbereiche werden standardmaessig nicht im Alltag gezeigt, bleiben aber fachlich im Katalog. Eine spaetere Einstellung kann ueber `activation_group_key` ganze optionale Bereiche aktivieren.

## Auswirkungen auf Dokumentationsstand, Schuelerprofil und Dashboard

Der Dokumentationsstand zaehlt weiterhin nur dokumentationsrelevante aktive Faechern und aktive Kompetenzen.

`learning_stage` ermoeglicht, offene Beobachtungsanlaesse passend zum Kurs oder zur gewaehlten Stufe zu priorisieren, ohne andere Kompetenzen zu verstecken.

Das Schuelerprofil kann historische Kompetenzstaende unveraendert zeigen und aktuelle Zielkompetenzen nach `learning_stage`, `active`, `catalog_status` und Dokumentationsrelevanz strukturieren.

Das Dashboard kann Handlungsbedarf aus Beobachtungen, bestaetigten Staenden und aktiven Katalogzielen ableiten. Es darf keine eigene Kataloglogik speichern.

## Empfohlene Architektur

Endgueltige Empfehlung:

1. CSV bleibt das pflegbare Seed- und Reviewformat des Katalogs.
2. SQLite speichert nach Import die operative Katalogprojektion vollstaendig genug fuer PySide, Berichte und Auswertungen.
3. `grade_band` bleibt Quellenkontext.
4. `learning_stage` wird als neues produktbezogenes Filterfeld eingefuehrt.
5. `active` bleibt lokale Arbeitsaktivitaet.
6. `catalog_default_active` speichert den CSV-Default fuer Erstimport und Reset-Logik.
7. `catalog_status` modelliert Bestandsschutz und fachliche Freigabe getrennt von Aktivitaet.
8. `activation_group_key` bereitet optionale Sportbereiche vor, ohne neue Sonderlogik in Widgets einzubauen.
9. Upsert aktualisiert fachliche Katalogmetadaten idempotent, schuetzt aber lokale Aktivierungsentscheidungen und historische Beobachtungen.
10. PySide-Widgets lesen nur ViewModels/Adapter-Projektionen und schreiben nicht direkt in SQLite.

## Offene Risiken

- Die konkrete Befuellung von `learning_stage` braucht fachliche Pruefung je Kompetenz.
- `catalog_status` ist zunaechst bewusst auf `current` und `legacy` begrenzt; weitere Statuswerte brauchen eine neue PO-Freigabe.
- Optional aktivierbare Sportbereiche brauchen eine separate UX- und Settings-Entscheidung.
- Historische Ansichten muessen spaeter entscheiden, ob sie aktuelle Katalogtexte oder beobachtungsnahe Snapshots bevorzugen.
- Bestehende CSV-Zeilen mit `grade_band = 1-4` duerfen nicht automatisch als `cross_stage` missverstanden werden, wenn die Fachpruefung eine Stufentrennung verlangt.
