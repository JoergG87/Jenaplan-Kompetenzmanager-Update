# Produktmodell-Vorschlag fuer Bericht und Lernentwicklungsgespraech

Status: Nicht bindender Architektur- und Product-Discovery-Vorschlag

Stand: 2026-07-14

Scope: Lernentwicklungsbericht, Lernentwicklungsgespraech (LEG), Vorschau, Abschluss, Versionierung, Snapshot und PDF-/Exportartefakte

Dieses Dokument bereitet Product-Owner-, Datenmodell-, Architektur-, UX- und Lifecycle-Entscheidungen vor. Es ist keine ADR, keine Schemafreigabe und keine Implementierungsfreigabe. Vorgeschlagene technische Namen sind noch nicht in `docs/TECHNICAL_NAMES.md` registriert.

## 1. Executive Summary

Der aktuelle Produktstand kann Berichtsentwuerfe und LEG-Arbeitsentwuerfe bereits dauerhaft speichern und erneut oeffnen. Gespeichert werden manuelle Texte, Zeitraum, verantwortliche Lehrkraft sowie bewusst ausgewaehlte Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen. Kompetenztexte, sichtbare Hierarchien, Kompetenzstaende, Beobachtungstexte, Schueler- und Gruppenkontext werden beim Oeffnen weiterhin live aus SQLite aufgebaut. Die Entwuerfe sind deshalb arbeitsfaehig, aber nicht historisch reproduzierbar.

Empfohlen wird Variante A in einer bewusst schmalen Form:

- Bericht und LEG bleiben getrennte fachliche Aggregate mit eigenen Status-, Abschluss- und Korrekturregeln.
- Gemeinsam genutzt werden nur ein versionierter Dokumentkopf, ein validierter Snapshot-Vertrag, neutrale Render-Modelle, Hashing, Dateipfadregeln und Exportartefakt-Metadaten.
- Es entsteht keine generische Workflow-Engine und keine universelle `documents`-Fachentitaet.
- Ein Entwurf liest operative Fachinformationen live, speichert aber Auswahlreferenzen und manuelle Inhalte.
- Eine Vorschau ist eine Projektion und kein persistierter Status.
- Bei `finalized` (Bericht) beziehungsweise `completed` (LEG) wird der ausgaberelevante fachliche Inhalt transaktional eingefroren. Die abgeschlossene Version ist danach unveraenderlich.
- Eine Korrektur entsperrt keine abgeschlossene Version, sondern erzeugt eine neue Revision. Erst deren Abschluss setzt die Vorgaengerversion auf `superseded`.
- Vorschau und PDF muessen dasselbe Render-Modell verwenden. Der Renderer liest weder Widgets noch SQLite und berechnet keine Fachlogik.
- Ein PDF ist ein abgeleitetes Artefakt. Fuer eine ausgegebene finale Version werden sowohl der reproduzierbare Snapshot als auch die tatsaechlich ausgegebene PDF-Datei mit Hash dauerhaft aufbewahrt.

Die naechste Implementierung darf erst nach den fuenf Product-Owner-Entscheidungen in Abschnitt 16 und nach der vorgeschriebenen Aktualisierung der bestehenden Governance-Dokumente beginnen.

## 2. Ist-Zustand

### 2.1 Bereits implementiert

#### Live-Berichtsvorschau im Schuelerprofil

`StudentDesktopAdapter.get_report_preview_for_student()` baut aus aktuellem Schuelerprofil, aktiven Beobachtungen, berechneten Kompetenzvorschlaegen und aktuellen Bestaetigungen eine live abgeleitete `StudentReportPreviewViewModel`-Projektion. Die Profilansicht zeigt aktuellen Stand, Staerken, Entwicklung, Unterstuetzungsbedarf und Beispielbeobachtungen. Soft-geloeschte Beobachtungen werden durch den aktiven Beobachtungslesepfad ausgeschlossen.

Diese Vorschau kann als Text in die Zwischenablage kopiert oder als `.md`/`.txt` an einen frei gewaehlten Pfad geschrieben werden. Der Export wird nicht registriert, nicht versioniert und nicht einem gespeicherten Berichtsentwurf zugeordnet.

#### Persistenter Berichtsentwurf und Berichtswerkstatt

Vorhanden sind:

- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`

Ein Berichtsentwurf speichert:

- `report_draft_id` im Format `RPD-######`
- `student_id`
- Berichtstyp `learning_development`
- `period_start` und `period_end`
- Status `draft`
- frei eingegebenen Lehrkraftnamen
- manuellen Gesamtblick
- vier manuelle Texte je ausgewaehltem Fach
- ausgewaehlte `subject_id`, `competency_id` und `observation_id`
- ausgewaehlte Diagrammtypen
- `created_at` und `updated_at`

Anlegen und Aktualisieren laufen ueber ViewModel, Desktop-Adapter, Application Service, Domain-Service, Repository und SQLite. Aktualisieren ersetzt die Relationen atomar. Beim Oeffnen laedt die Shell den zuletzt aktualisierten Entwurf des Kindes.

Nicht gespeichert werden Schuelername, Stammgruppen- oder Kursname, sichtbare Fach-/Bereichs-/Themen-/Kompetenzlabels, Kompetenzstaende, Beobachtungsdatum, Kontext, Notiz, Bewertungen, Bestaetigungen, Diagrammdaten oder Dateien. Diese Inhalte werden live neu aufgeloest.

#### PDF-Weg fuer den Berichtsentwurf

Die Berichtswerkstatt baut aus aktuellem Widget-/Draftzustand und aktuellen Leseprojektionen ein fluechtiges `ReportOutputModel`. `PdfRenderer` aus `prototypes/pdf_engine/` rendert dieses Modell mit ReportLab. Der Renderer liest keine Datenbank und berechnet keine Kompetenzlogik.

Das PDF kann jedoch aus ungespeicherten Aenderungen erzeugt werden. Es wird an einem frei gewaehlten Pfad gespeichert, nicht registriert, nicht gehasht, nicht versioniert und nicht sicher mit dem gespeicherten Draft verbunden. Der Standarddateiname enthaelt den aktuellen Schuelernamen. `created_on` wird beim Modellaufbau aus dem aktuellen Tagesdatum gesetzt.

#### Persistenter LEG-Arbeitsentwurf und sechs Phasen

Vorhanden sind:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Ein LEG-Arbeitsentwurf speichert:

- `learning_conference_draft_id` im Format `LCD-######`
- `student_id`
- optionalen Zeitraum und Gespraechsdatum
- Status `draft`
- verantwortliche Lehrkraft als Text
- Gespraechseinstieg, Kindrueckblick, Lehrkraftsicht, Staerken und Entwicklungsfelder
- getrennte vorbereitete und gemeinsam vereinbarte Ziele, Unterstuetzungen und Vereinbarungen
- Zustaendigkeiten und naechsten Ueberpruefungszeitpunkt
- Fach-, Querschnittsthemen-, Kompetenz-, Beobachtungs- und Diagrammreferenzen
- `created_at` und `updated_at`

Die produktive Dialogprojektion zeigt gleichzeitig Vorbereitung und Gespraechsmappe mit sechs Phasen:

1. Gespraechsziel
2. Was gelingt dem Kind?
3. Welche Entwicklung sehen wir?
4. Woran moechten wir gemeinsam arbeiten?
5. Welche Beispiele stuetzen unsere Einschaetzung?
6. Welche Unterstuetzung und Vereinbarungen treffen wir?

Bei genau einem Draft wird dieser direkt geladen; bei mehreren Drafts gibt es eine Auswahl. Bereits referenzierte, spaeter soft-geloeschte Beobachtungen bleiben als ID erhalten und werden als nicht mehr verfuegbar angezeigt. Der LEG-Entwurf besitzt keinen Abschluss, keine Versionierung, kein Archiv und keinen Export.

#### Schema und Migrationstechnik

`SQLiteDatabase.initialize_schema()` ergaenzt die Draft-Tabellen ueber idempotente `CREATE TABLE IF NOT EXISTS`-Anweisungen. Es gibt fuer diese Schritte keine eigene Schema-Versionstabelle und keinen separaten Migrationsrunner. Tests pruefen die additive Anlage auf einer bestehenden Datenbank und den Erhalt vorhandener Stammdaten.

Die am 2026-07-14 gepruefte produktive Datei `data/kompetenzmanager.sqlite` enthaelt alle Bericht-/LEG-Drafttabellen, aber jeweils null Berichtsdrafts und null LEG-Drafts. Daraus folgt nicht, dass andere lokale Installationen ebenfalls leer sind.

### 2.2 Dokumentiert, aber nicht implementiert

- eigene stabile Bericht- und LEG-Identitaet ausserhalb der Draft-IDs
- Abschluss beziehungsweise Finalisierung
- unveraenderliche Versionen und Revisionsnummern
- `superseded`- und Archivierungslogik
- eingefrorener Snapshot
- Pruefung/Freigabe, Rollen oder Signatur
- Exportartefakt-Registry, Hash und Renderer-Manifest
- studentenzentrierte Ablage finaler PDFs
- LEG-Abschlussansicht und LEG-Export
- Datenschutz-, Aufbewahrungs- und Loeschregeln fuer abgeschlossene Fassungen

ADR-050 beschreibt die Zielrichtung eines eingefrorenen, versionierten Berichts und eines reinen PDF-Renderers. ADR-052 und ADR-053 grenzen die heutigen Drafts ausdruecklich von finalen Domains ab. Der konkrete Lebenszyklus und das konkrete Snapshotmodell sind dennoch nicht beschlossen oder implementiert.

### 2.3 Im Pilottest erwartet

`docs/LAURA_PILOTTEST.md` prueft die alte live abgeleitete Berichtsvorschau, Bestaetigungen, Beobachtungsbelege und Dokumente. Die persistente Berichtswerkstatt, Entwurfsauswahl, PDF-Erzeugung, der LEG-Arbeitsbereich, die sechs Phasen, Abschluss, historische Fassungen und Korrekturen sind dort nicht als eigener Testweg enthalten.

### 2.4 Offen oder widerspruechlich

- `docs/DATA_LIFECYCLE.md` und `docs/VIEW_DATA_OWNERSHIP.md` formulieren, die separate Berichtsvorschau baue ihr `ReportOutputModel` aus dem Draft. Im Code rendert die Qt-Vorschau eigene Widgets und Hilfsmethoden; nur der PDF-Weg baut tatsaechlich das neutrale Modell. Vorschau und PDF besitzen daher aktuell keinen gemeinsamen Render-Contract.
- `prototypes/pdf_engine/README.md` nennt die PDF-Engine nicht produktiv integriert. Die produktive Shell importiert den Renderer inzwischen direkt aus dem Prototyp-Pfad. Technisch ist er angebunden, organisatorisch und paketstrukturell bleibt er ein Prototyp.
- Die Dokumentation verspricht aufloesbare historische Berichtskompetenzreferenzen. Die Berichtsvorbereitung uebergibt anders als LEG keine `retained_competency_ids`; das Ausgabemodell filtert zudem nicht mehr auswaehlbare Kompetenzen aus. Eine nachtraeglich deaktivierte Auswahl kann deshalb aus der Ausgabe verschwinden.
- LEG kennzeichnet spaeter geloeschte Beobachtungen kontrolliert. Der Bericht speichert die Referenz, bietet aber keinen gleichwertigen Nicht-verfuegbar-Zustand und laesst die Beobachtung in der live aufgebauten Ausgabe weg.
- Der neue Bericht kennt in seinem Render-Modell Stammgruppe, aber keinen expliziten Kurskontext. Anhange werden weder in Bericht noch LEG einbezogen.
- ADR-050 listet neun offene Product-Owner-Fragen. Dieser Vorschlag konsolidiert sie auf fuenf notwendige Entscheidungen, ohne ADR-050 umzuschreiben.
- Der Discovery-Auftrag ist als Sprint 5A bezeichnet, waehrend die vorhandene Historie Bericht/LEG bereits unter Sprint 7 fuehrt. Das ist eine Planungsbezeichnung, keine technische Version oder Migration.

### 2.5 Wo heutige Aenderungen rueckwirkend wirken

| Spaetere Aenderung | Wirkung auf heutigen Berichtsdraft | Wirkung auf heutigen LEG-Draft |
| --- | --- | --- |
| Beobachtungstext, Datum, Kontext oder Bewertung geaendert | Vorschau/PDF zeigt neue Werte | Gespraechsmappe zeigt neue Werte |
| Beobachtung soft-geloescht | Beleg verschwindet ohne gleichwertige historische Darstellung | Referenz bleibt als nicht verfuegbar sichtbar, Inhalt fehlt |
| Kompetenz umbenannt | neuer Text und neue Hierarchie erscheinen | neuer Text und neue Hierarchie erscheinen |
| Kompetenz deaktiviert/legacy | kann in Berichtsausgabe verschwinden | bleibt bei gespeicherter Referenz historisch sichtbar |
| Kompetenz bestaetigt oder neu beobachtet | aktueller Stand und Diagrammpunkte aendern sich | interner Vorbereitungsstand aendert sich |
| Schueler umbenannt oder Stammgruppe gewechselt | neuer Name/neue Gruppe erscheinen | neuer Name/neue Gruppe erscheinen |
| Kurs umbenannt/gewechselt | aktueller Bericht bildet Kurs nicht explizit ab | aktuelles LEG bildet Kurs nicht explizit ab |
| Lehrkraft im Draft geaendert | Drafttext aendert sich | Drafttext aendert sich |
| ausgewaehlter Anhang entfernt | derzeit ohne Wirkung, da nicht integriert | derzeit ohne Wirkung, da nicht integriert |

## 3. Fachliche Begriffe

**Live-Profil:** Aktuelle Arbeitsansicht des Kindes. Es zeigt den heutigen operativen Stand und besitzt keine historische Dokumentaussage.

**Entwurf:** Bearbeitbarer Arbeitsstand mit manuellen Inhalten und bewussten Referenzauswahlen. Operative Fachinhalte werden weiterhin live aufgeloest.

**Vorschau:** Read-only-Darstellung des gerade wirksamen Render-Modells. Eine Vorschau ist kein eigener Persistenzstatus und keine Freigabe.

**Finalisierung/Abschluss:** Explizite fachliche Aktion, die eine neue unveraenderliche Version und ihren Snapshot erzeugt. Beim Bericht heisst der technische Zielstatus `finalized`, beim LEG `completed`.

**Version:** Unveraenderliche oder noch bearbeitbare Fassung innerhalb einer stabilen fachlichen Identitaet. Die erste Fassung hat Revision 1; Korrekturen erhoehen die Revision.

**Snapshot:** Vollstaendiger, versionierter und validierter fachlicher Ausgabestand einer abgeschlossenen Version. Er enthaelt alle zur historischen Darstellung benoetigten Werte, aber keine unselektierte operative Datenbankkopie.

**Render-Modell:** Vollstaendige, UI- und renderer-neutrale Darstellungseingabe. Vorschau und PDF konsumieren dasselbe Modell.

**Exportartefakt:** Aus einem unveraenderlichen Render-Modell erzeugte Datei einschliesslich Pfad, Hash, Renderer-Version und Erzeugungszeitpunkt. Es ist nicht die fachliche Quelle.

**Korrektur:** Neue Draft-Version derselben fachlichen Identitaet. Sie veraendert die abgeschlossene Vorgaengerversion nicht.

**Folgegespraech:** Neues LEG mit eigener stabiler Identitaet und optionalem Verweis auf das vorherige LEG. Es ist keine Korrekturversion des alten Gespraechs.

**Archivierung:** Ausblenden eines gesamten Berichts beziehungsweise LEG aus den aktiven Arbeitslisten bei unveraendertem Erhalt aller Versionen und Artefakte.

## 4. Lebenszyklus Bericht

### 4.1 Verbindlich empfohlene Zustaende

| Fachlicher Zustand | Technischer Status | Bearbeitbar | Live gelesen | Gespeichert/eingefroren | Ausloesende Aktion |
| --- | --- | --- | --- | --- | --- |
| Neuer Entwurf | noch kein Datensatz | ja | kompletter aktueller Auswahlkontext | nur lokaler UI-Zustand | `Neuen Entwurf anlegen` |
| Gespeicherter Entwurf | `draft` | ja | Labels, Staende, Beobachtungsinhalte, Stammdaten | manuelle Texte, Zeitraum, Lehrkraft, Auswahl-IDs, Zeitstempel | `Entwurf speichern` |
| Vorschau | kein eigener Status | nein in der Vorschau; Draft bleibt bearbeitbar | bei Draft-Vorschau live | fluechtiges Render-Modell | `Vorschau pruefen` |
| Finalisierte Fassung | `finalized` | nein | nichts fuer den Dokumentinhalt | kompletter Snapshot, Revision, Autor-/Finalisierungsmetadaten, Hash | `Bericht finalisieren` nach Validierung und Warnung |
| PDF erzeugt | kein Dokumentstatus | nein | nichts | neues Exportartefakt zur finalisierten Version | `PDF erzeugen` |
| Korrektur in Arbeit | neue Version `draft` | ja | aktueller Kontext plus kopierte Inhalte der Vorgaengerversion | eigene neue Version mit `supersedes_version_id` | `Korrektur als neue Version beginnen` |
| Ersetzte Fassung | `superseded` | nein | nichts | alter Snapshot und alle Artefakte bleiben erhalten | Abschluss der Korrekturversion |
| Archiviert | Aggregatebene `archived_at` | nein | nichts | alle Versionen und Artefakte bleiben erhalten | `Bericht archivieren` |

### 4.2 Regeln

- Pro `report_id` darf hoechstens eine bearbeitbare Draft-Version existieren.
- Pro `report_id` darf hoechstens eine aktuelle finalisierte Version existieren.
- `Vorschau` und `PDF erzeugt` sind keine Statuswerte.
- Finalisierung erfolgt transaktional: validieren, Snapshot bauen, Snapshot-Hash berechnen, Version sperren und Finalisierungsmetadaten schreiben oder alles zurueckrollen.
- Eine Finalisierung wird nicht rueckgaengig gemacht. Ein Bedienfehler wird als Korrekturversion behandelt.
- Eine neue Draft-Korrektur macht die alte finale Version noch nicht `superseded`. Erst die Finalisierung der neuen Revision ersetzt sie.
- Eine abgebrochene Korrektur kann verworfen werden; die bisherige finale Version bleibt aktuell.
- Archivierung betrifft die stabile Berichtsidentitaet, nicht einzelne historische Versionen.

## 5. Lebenszyklus LEG

### 5.1 Verbindlich empfohlene Zustaende

| Fachlicher Zustand | Technischer Status | Bearbeitbar | Live gelesen | Gespeichert/eingefroren | Ausloesende Aktion |
| --- | --- | --- | --- | --- | --- |
| Vorbereitung begonnen | noch kein Datensatz oder `draft` | ja | aktuelle Kompetenz-/Evidenzprojektion | Rahmen, manuelle Vorbereitung, Auswahlreferenzen nach Speichern | `LEG vorbereiten` / `Entwurf speichern` |
| Belege ausgewaehlt | `draft` | ja | aktuelle Labels, Staende und Belegtexte | Auswahl-IDs | Speichern |
| Gespraech laeuft | weiterhin `draft` | ja | aktueller vorbereitender Kontext | alle manuellen Zwischenstaende | `Gespraech starten` (UI-Modus, kein eigener Persistenzstatus) |
| Gemeinsam erarbeitete Inhalte | `draft` | ja | aktuelle Kontextprojektion | getrennte vereinbarte Ziele, Unterstuetzung, Vereinbarungen | Speichern waehrend/nach Phase 6 |
| Abgeschlossen | `completed` | nein | nichts fuer die historische Gespraechsfassung | kompletter, datensparsamer LEG-Snapshot | `Gespraech abschliessen` |
| Nachtraegliche Korrektur | neue Version `draft` | ja | aktueller Kontext plus kopierte Inhalte | neue Revision mit Vorgaengerbezug | `Korrektur beginnen` |
| Ersetzte Fassung | `superseded` | nein | nichts | alte Fassung bleibt erhalten | Abschluss der Korrekturversion |
| Archiviert | Aggregatebene `archived_at` | nein | nichts | alle Versionen bleiben erhalten | `LEG archivieren` |

### 5.2 Regeln

- `Gespraech starten` ist zunaechst ein UI-/Zeitstempelereignis, kein zusaetzlicher Workflowstatus. Optional kann `started_at` gespeichert werden.
- Der Abschluss friert nur fachlich zweckgebundene Inhalte ein. Interne, nicht in das Gespraechsergebnis uebernommene Vorbereitung wird nach der Empfehlung in Abschnitt 16 nicht Teil der finalen Gespraechsfassung.
- Ein abgeschlossenes LEG wird nicht wieder bearbeitbar geschaltet.
- Eine Korrektur desselben Gespraechs erzeugt Revision 2, 3 und so weiter.
- Ein neuer Ueberpruefungs- oder Folgetermin ist fachlich ein neues LEG mit eigener `learning_conference_id` und optionalem `follows_up_learning_conference_id`, keine neue Revision des alten Termins.
- Ein spaeteres LEG-PDF ist optional. Der Abschluss darf nicht davon abhaengen, ob ein PDF benoetigt wird.

## 6. Live-Daten versus Snapshot

### 6.1 Antworten auf die Kernfragen

1. **Entwuerfe sollen aktuelle Daten weiterhin live anzeigen.** Das ist fuer die laufende Arbeit gewollt. Aenderungen an bereits ausgewaehlten Quellen muessen jedoch als `geaendert`, `nicht mehr verfuegbar` oder `historisch` sichtbar werden und duerfen Referenzen nicht still entfernen.
2. **Ausgewaehlte Kompetenzen und Belege werden bereits beim Speichern des Entwurfs fest zugeordnet.** Das entspricht dem heutigen Modell und bleibt bestehen. Die ID-Zuordnung ist fest, der angezeigte Inhalt bleibt bis zum Abschluss live.
3. **Beim Abschluss wird das vollstaendige ausgaberelevante Fachmodell eingefroren.** Stabile Referenzen allein reichen nicht. IDs bleiben fuer Herkunft und Navigation enthalten, aber alle historisch sichtbaren Werte werden zusaetzlich als Snapshotwert gespeichert.
4. **Der Snapshot enthaelt vollstaendige selektierte Fachinhalte, nicht die gesamte operative Datenbank.** Unselektierte Beobachtungen, Kompetenzen, Dokumente und Historien werden nicht kopiert.

### 6.2 Inhalt des Snapshots

| Inhalt | Draft | Bei Abschluss einfrieren |
| --- | --- | --- |
| Schueler | `student_id` gespeichert, Name live | ID und sichtbarer Name |
| Stammgruppe | live | `group_id` und sichtbarer Name |
| Kurskontext | heute weitgehend fehlend/live | relevante `course_id`/Kursverbund-ID und sichtbare Namen, sofern fuer Dokumenttyp vorgesehen |
| Schuljahr/Zeitraum | Zeitraum gespeichert | Zeitraum, abgeleitetes Schuljahr nur nach klarer Regel |
| Lehrkraft | freier Name gespeichert | verantwortlicher Anzeigename; spaeter optional stabile Benutzer-ID |
| Schule/Dokumenttyp | teilweise Default/live | sichtbarer Schulname, Dokumenttyp und Sprach-/Layoutkontext |
| Fach/Bereich/Thema/Kompetenz | IDs gespeichert, Labels live | IDs, sichtbare Labels und Hierarchie |
| Kompetenzstand | live aus kanonischer Projektion | ausgewaehlter Stand, Quelle (`confirmed`/`observed`), Stichtag und fuer Darstellung benoetigte Evidenzpunkte |
| Beobachtung | ID gespeichert, Inhalt live | ID, Datum, Fach, Kontext, Notiz, ausgewaehlte Ratingzeilen und Verfuegbarkeitszustand zum Abschluss |
| Manuelle Berichtstexte | gespeichert | unveraendert einfrieren |
| LEG-Vorbereitung | gespeichert | nur nach Product-Owner-Regel; empfohlen nicht automatisch in die Abschlussfassung uebernehmen |
| LEG-Ergebnisse | gespeichert | gemeinsam vereinbarte Ziele, Unterstuetzung, Vereinbarungen, Zustaendigkeiten, Ueberpruefungstermin |
| Diagramme | Typ gespeichert, Daten live | Typ, vollstaendige Darstellungsdaten, Labels, Zeitraum und Legende |
| Anhaenge | derzeit nicht integriert | nur bewusst einbezogene Metadaten plus unveraenderliche Dateikopie und Hash |
| Render-Metadaten | fluechtig | Snapshot-Schema, Locale, Builder-Version, Snapshot-Hash, `frozen_at` |

### 6.3 Verhalten nach Abschluss

- **Beobachtung bearbeitet oder soft-geloescht:** Live-Profil und neue Drafts zeigen den neuen Zustand. Die abgeschlossene Version behaelt Text, Bewertung und Kennzeichnung aus dem Snapshot.
- **Kompetenz umbenannt oder deaktiviert:** Neue Ansichten verwenden den neuen Katalogstand. Die abgeschlossene Version behaelt historische Labels und Hierarchie; die ID bleibt als Herkunftsnachweis enthalten.
- **Stammgruppenwechsel:** Live-Profil zeigt die neue Stammgruppe. Die abgeschlossene Fassung behaelt die Gruppe zum Abschlusszeitpunkt.
- **Kurs umbenannt/gewechselt:** Gleiches Prinzip wie bei der Stammgruppe.
- **Lehrkraft geaendert:** Eine neue Verantwortlichkeit wirkt nicht rueckwirkend. Die finale Version behaelt Autor-/Finalisierungsangaben.
- **Anhang entfernt:** Ein nur live referenzierter Anhang kann verschwinden. Deshalb wird ein bewusst in eine finale Fassung aufgenommener Anhang beim Abschluss in den versionierten Dokumentordner kopiert und gehasht. Nicht ausgewaehlte Dateien werden nicht dupliziert.

## 7. Versionierung

### 7.1 Vorgeschlagene technische Identitaeten

Die Namen sind Vorschlaege und vor Implementierung zu registrieren:

| Konzept | Vorgeschlagener Name | Regel |
| --- | --- | --- |
| stabiler Bericht | `report_id` (`RPT-######`) | bleibt ueber alle Revisionen stabil |
| Berichtsversion | `report_version_id` (`RPV-######`) | unveraenderliche technische Identitaet einer Revision |
| Berichtsrevision | `revision` | positive, je `report_id` eindeutige Ganzzahl ab 1 |
| stabiles LEG | `learning_conference_id` (`LCF-######`) | identifiziert genau einen Gespraechsanlass |
| LEG-Version | `learning_conference_version_id` (`LCV-######`) | technische Identitaet einer Revision |
| Exportartefakt | `export_artifact_id` (`XPA-######`) | identifiziert genau eine erzeugte Datei |
| separater Snapshot | vorerst keiner | Snapshot ist 1:1 Bestandteil der finalen Version |

Ein eigener `snapshot_id` bringt im ersten Schnitt keinen fachlichen Nutzen. Empfohlen werden stattdessen `snapshot_schema_version`, `snapshot_payload`, `snapshot_hash` und `frozen_at` an der jeweiligen finalen Version beziehungsweise in einer strikt 1:1 zugeordneten domainspezifischen Snapshottabelle. Dadurch kann kein Snapshot versehentlich zwischen Bericht und LEG geteilt werden.

### 7.2 Statusmodelle

Berichtsversion:

```text
draft -> finalized -> superseded
```

LEG-Version:

```text
draft -> completed -> superseded
```

Archivierung liegt auf der stabilen Aggregatebene ueber `archived_at`, `archived_by` und optional `archive_reason`. `pdf_generated`, `preview`, `corrected` und `finished` sind keine Statuswerte.

### 7.3 Pflichtmetadaten

Jede Aggregatebene besitzt stabile ID, `student_id`, Dokument-/Gespraechstyp, `created_at`, `created_by` soweit eine Benutzeridentitaet existiert, und Archivierungsmetadaten.

Jede Version besitzt Versions-ID, Aggregate-ID, `revision`, Status, `created_at`, `created_by`, `updated_at`, `updated_by`, Abschlusszeitpunkt und Abschlussakteur, optional `supersedes_version_id`, Korrekturgrund, Snapshot-Schemaversion und Snapshot-Hash.

Solange keine Benutzer-/Rollenentitaet existiert, muss mindestens der verantwortliche Anzeigename eingefroren werden. Eine scheinbar stabile Benutzer-ID darf nicht vorweggenommen werden.

### 7.4 Soft Delete

Finalisierte beziehungsweise abgeschlossene Versionen werden nicht soft-geloescht. Sie werden ersetzt oder das gesamte Aggregat wird archiviert. Fuer nie abgeschlossene Drafts kann spaeter ein expliziter Prozess `Entwurf verwerfen` vorgesehen werden; dessen Aufbewahrungsregel ist eine Datenschutzentscheidung und kein versteckter `active`-Schalter.

## 8. Gemeinsames beziehungsweise getrenntes Modell

### 8.1 Variante A: schmale gemeinsame Infrastruktur, getrennte Aggregate

Gemeinsam:

- `DocumentContextSnapshot` als versionierter Wertvertrag
- Snapshot-Serialisierung, Validierung und Hashing
- Render-Modell-Basis fuer Metadaten, Seiten und Bloecke
- Exportartefakt-Service, Pfadpolicy und Integritaetspruefung
- gemeinsame technische Regeln fuer Zeitstempel, Revision und Unveraenderlichkeit

Getrennt:

- Berichtsdomain, Berichtstexte, Fachseiten und Status `finalized`
- LEG-Domain, sechs Phasen, gemeinsam vereinbarte Inhalte und Status `completed`
- Repositories, Application Commands und Finalisierungsvalidatoren
- domainspezifische Snapshot-Payloads und Render-Modelle

### 8.2 Variante B: vollstaendig getrennte Modelle

Bericht und LEG erhalten auch fuer Dokumentkopf, Snapshot, Hash, Artefakte, Pfade und Renderer-Metadaten jeweils eigene Implementierungen.

### 8.3 Bewertung und Empfehlung

| Kriterium | Variante A | Variante B |
| --- | --- | --- |
| Fachliche Klarheit | hoch, wenn nur Infrastruktur geteilt wird | sehr hoch, aber technische Doppelung |
| Wartbarkeit | hoch durch eine Artefakt-/Snapshotpolicy | sinkt bei zwei fast gleichen Infrastrukturpfaden |
| Testbarkeit | gemeinsame Contract-Tests plus Domain-Tests | viele doppelte Tests |
| Erweiterbarkeit | kontrolliert fuer spaetere Exportformate | jede Erweiterung zweimal |
| Migrationsrisiko | moderat | moderat bis hoch durch parallele Mechanismen |
| Gefahr der Uebergeneralisierung | beherrschbar durch klare Grenze | gering |

Empfohlen wird **Variante A**. Gemeinsam ist nur die dokumenttechnische Infrastruktur. Bericht und LEG teilen weder Fachfelder noch Statusautomaten noch eine generische Workflowtabelle. Eine Universal-Workflow-Engine, frei konfigurierbare Statusketten oder ein untypisiertes Schluessel-Wert-Dokumentmodell sind ausdruecklich ausgeschlossen.

## 9. Vorschau und PDF

### 9.1 Zielcontract

```text
Draft + aktuelle freigegebene Leseprojektionen
-> domainspezifischer Composer
-> validiertes Render-Modell
-> Qt-Vorschau und optionaler Entwurfs-PDF-Renderer

finaler Snapshot
-> Deserialisierung in dasselbe validierte Render-Modell
-> historische Qt-Vorschau und finaler PDF-Renderer
```

Die Qt-Vorschau liest keine Widgets direkt zusammen, sondern rendert das gleiche Modell, das an PDF uebergeben wird. Visuelle Implementierungen duerfen unterschiedlich sein; Dokumentinhalt, Reihenfolge, Tabellenzeilen, Diagrammdaten und Metadaten muessen identisch aus demselben Contract stammen.

### 9.2 Entwurfs- und finale PDFs

- Ein Entwurfs-PDF darf optional erzeugt werden, traegt aber gut sichtbar `ENTWURF`, wird nicht als offizielles Exportartefakt registriert und kann nach jeder Aenderung veraltet sein.
- Ein finales PDF kann nur aus einer `finalized`-Berichtsversion beziehungsweise spaeter aus einer `completed`-LEG-Version erzeugt werden.
- Der Renderer hat keine SQLite-, Repository-, Service- oder Widgetabhaengigkeit.
- Ein fachlich finaler Snapshot darf auch dann unveraendert lesbar bleiben, wenn spaeter ein neuer Renderer eingefuehrt wird.

### 9.3 Ablage, Dateiname und Metadaten

Empfohlener verwalteter Pfad fuer Berichte:

```text
data/documents/<student_id>/reports/<report_id>/<report_version_id>/
```

Empfohlener Dateiname ohne Klarname:

```text
Lernentwicklungsbericht_<student_id>_<period_end>_v<revision>_<report_version_id>.pdf
```

Ein spaeter freigegebener LEG-Export folgt analog unter `learning_conferences/`. Klarnamen im Dateinamen werden wegen Datenschutz, Umbenennbarkeit und Dateisystemweitergabe nicht empfohlen.

Zu jedem Artefakt werden mindestens gespeichert:

- `export_artifact_id`
- Dokumentart und Versions-ID
- relativer verwalteter Pfad und Dateiname
- MIME-Type und Dateigroesse
- SHA-256 des Snapshots und der Datei
- Renderer-/Template-Version und verwendete Font-/Layoutkennung
- Erzeugungszeitpunkt und Erzeuger
- Artefaktfolge beziehungsweise Grund einer Neuerzeugung

Erneute Exporte ueberschreiben keine vorhandene Datei. Sie erzeugen ein neues Artefakt mit eigener ID und eigenem Hash. Ein altes finales PDF wird durch spaetere operative Daten nicht ungueltig. Es kann nur durch eine neue fachliche Version ersetzt oder durch eine fehlgeschlagene Integritaetspruefung als beschaedigt markiert werden.

### 9.4 Geeignete Bordmittel, nur konzeptionell

- Das bestehende ReportLab-Modell erfuellt die wichtige Trennung zwischen Render-Modell und PDF-Renderer und kann als technische Ausgangsbasis bewertet werden.
- Qt-Druckklassen koennen fuer Druckvorschau oder einfachen Druck technisch geeignet sein, duerfen aber nicht dazu fuehren, Widgets als Dokumentquelle zu verwenden.
- HTML/CSS-zu-PDF waere eine alternative Rendertechnologie, verlangt jedoch dieselbe neutrale Eingabe, deterministische Fonts und reproduzierbare Seitenumbrueche.

Die Bibliothekswahl ist nachrangig gegenueber Snapshot-, Render- und Artefaktcontract. In diesem Sprint wird keine Bibliothek installiert oder festgelegt.

## 10. UI-Folgen

### 10.1 Bericht

Primäre Aktionen je Zustand:

- ohne Draft: `Neuen Berichtsentwurf anlegen`
- Draft: `Entwurf speichern`, `Vorschau pruefen`, sekundaer `Entwurfs-PDF`
- finalisierungsbereit: `Bericht finalisieren`
- finalisiert: `PDF erzeugen`, `Historische Fassung oeffnen`, `Korrektur als neue Version beginnen`
- archiviert: `Archivierte Fassung oeffnen`; Wiederaktivierung nur nach eigener Regel

StatusBadges:

- `Entwurf`
- `Finalisiert · Version 1`
- `Ersetzt · Version 1`
- `Archiviert`

Vor Finalisierung zeigt die UI eine Zusammenfassung von Zeitraum, Lehrkraft, fehlenden Pflichtinhalten, nicht verfuegbaren Referenzen, ausgewaehlten Belegen und Anhaengen. Die Warnung muss sagen, dass die Fassung danach schreibgeschuetzt bleibt und Korrekturen eine neue Version erzeugen.

### 10.2 LEG

Primäre Aktionen:

- `LEG vorbereiten`
- `Entwurf speichern`
- `Gespraech starten`
- waehrend der sechs Phasen `Zwischenstand speichern`
- nach Phase 6 `Gespraech abschliessen`
- abgeschlossen `Abgeschlossene Fassung oeffnen`
- Fehlerkorrektur `Korrektur als neue Version beginnen`
- neuer Termin `Folgegespraech anlegen`

StatusBadges:

- `Vorbereitung / Entwurf`
- `Abgeschlossen · Version 1`
- `Ersetzt · Version 1`
- `Archiviert`

`Gespraech gestartet` kann als zeitlicher Hinweis erscheinen, ist aber kein eigener dauerhafter Workflowstatus. Vor Abschluss muss die UI gemeinsam vereinbarte Inhalte klar von interner Vorbereitung trennen und anzeigen, welche Inhalte in die Abschlussfassung gelangen.

### 10.3 Unterschiede der Ansichten

| Ansicht | Datencharakter | Bearbeitung | Historische Aussage |
| --- | --- | --- | --- |
| Live-Profil | aktueller operativer Stand | ueber bestehende Fachprozesse | nein |
| Entwurf | gespeicherte Autorentexte/Referenzen plus Live-Kontext | ja | nein |
| Vorschau eines Drafts | aktuelles fluechtiges Render-Modell | nein | nein, als Entwurf kennzeichnen |
| Finalisierte/abgeschlossene Fassung | Snapshot einer Version | nein | ja |
| PDF | Artefakt einer finalen Version | nein | ja, wenn Hash/Version zugeordnet |

## 11. Migrationsfolgen

### 11.1 Zu uebernehmende Daten

Alle Spalten und Relationen aus `report_drafts*` und `learning_conference_drafts*` muessen uebernommen werden. `created_at`, `updated_at`, die bestehenden Draft-IDs, manuelle Texte und jede Auswahlreferenz sind erhaltenswert.

### 11.2 Eindeutigkeit der Migration

- Jeder vorhandene Berichtsdraft wird zu einem eigenen `report_id` mit Revision 1 und Status `draft`.
- Jeder vorhandene LEG-Draft wird zu einer eigenen `learning_conference_id` mit Revision 1 und Status `draft`.
- Mehrere Drafts desselben Kindes oder Zeitraums werden nicht automatisch zusammengefuehrt und nicht als Versionen voneinander interpretiert.
- Die alten IDs werden als Migrationsherkunft erhalten oder ueber eine eindeutige Zuordnungstabelle nachvollziehbar gemacht.

Damit sind bestehende Drafts strukturell eindeutig migrierbar. Nicht rekonstruierbar sind historische Labels oder Inhalte zu einem frueheren Bearbeitungszeitpunkt, weil Drafts diese Werte nie eingefroren haben. Das ist fuer weiter live arbeitende Drafts akzeptabel; sie duerfen nicht rueckwirkend als historische Fassungen ausgegeben werden.

### 11.3 Defaults

- `revision = 1`
- Status bleibt `draft`
- `finalized_at`, `completed_at`, `supersedes_version_id`, `snapshot_payload`, `snapshot_hash` und Archivierungsfelder bleiben leer
- vorhandene Lehrkrafttexte bleiben erhalten
- keine automatische Ableitung einer Benutzer-ID, Freigabe oder eines Schuljahres

### 11.4 Migrationsstrategie und Rollback

Eine additive Migration reicht fachlich aus und ist empfohlen:

1. neue Aggregate-/Versionstabellen additiv anlegen
2. Drafts in einer Transaktion kopieren
3. Mengen, IDs und Relationserhalt pruefen
4. Anwendung auf neuen Lese-/Schreibpfad umstellen
5. alte Drafttabellen zunaechst read-only erhalten

Rollback bedeutet, auf die vorherige App-Version und die unangetasteten alten Drafttabellen zurueckzugehen. Eine destruktive Down-Migration oder das Loeschen der neuen Tabellen ist nicht erforderlich. Die alten Tabellen duerfen erst in einem spaeteren, separat freigegebenen Cleanup entfernt werden.

### 11.5 Betroffene Tests und Seeds

Direkt betroffen waeren:

- `tests/test_report_draft.py`
- `tests/test_learning_report.py`
- `tests/test_learning_conference_draft.py`
- `tests/test_learning_conference_ui.py`
- SQLite-Schema-/Migrationspruefungen in `tests/test_sqlite_spike.py`
- neue Contract-Tests fuer Snapshot, Hash, Revision, Finalisierung, Korrektur und Artefakte

Der produktionsnahe Seed erzeugt aktuell keine Bericht- oder LEG-Drafts. Fuer Migrationstests sind gezielte alte-Schema-Fixtures geeigneter als eine Aufladung des allgemeinen Pilotseeds. Falls der Pilottest spaeter historische Fassungen pruefen soll, braucht er separat freigegebene synthetische Report-/LEG-Versionen.

## 12. Datenschutz- und Historisierungsfolgen

- Snapshots enthalten besonders sensible paedagogische Daten und muessen datensparsam auf genau den Dokumentzweck begrenzt sein.
- Interne LEG-Vorbereitung und gemeinsam vereinbarte Ergebnisse benoetigen unterschiedliche Aufbewahrungsregeln.
- Eine finale Fassung darf nicht durch das Loeschen operativer Quellen zerstoert werden. Historisierung ist fuer selektierte Inhalte zweckgebunden erforderlich.
- Nicht ausgewaehlte Beobachtungen, vollstaendige Schuelerakten und allgemeine Dokumentordner werden nicht in den Snapshot kopiert.
- Eingebundene Anhaenge werden nur nach bewusster Auswahl kopiert; Pfad, Hash, MIME-Type und urspruenglicher Anzeigename werden festgehalten.
- Dateinamen finaler Artefakte verwenden technische IDs statt Klarnamen.
- Frei gewaehlte externe Exportpfade liegen ausserhalb der verwalteten Aufbewahrung. Die UI muss diesen Unterschied klar benennen.
- Backup, Restore, Zugriffsschutz, Aufbewahrungsdauer und sichere Loeschung archivierter Drafts muessen vor echtem Schuleinsatz geregelt sein. Die derzeit lokale SQLite-/Dateiablage liefert noch kein Rollen- oder Berechtigungssystem.
- Hashes sichern Integritaet, ersetzen aber weder Zugriffsschutz noch Verschluesselung.

## 13. Risiken und Trade-offs

| Risiko/Trade-off | Bewertung | Gegenmassnahme |
| --- | --- | --- |
| Snapshot dupliziert Daten | bewusst begrenzte Duplizierung ist fuer Historie noetig | nur selektierte sichtbare Inhalte einfrieren |
| IDs ohne Inhalte reichen nicht | alte Dokumente wuerden sich veraendern | IDs plus historische Labels und Werte speichern |
| Vollstaendige DB-Kopie im Snapshot | unnoetig und datenschutzkritisch | domainspezifischer Snapshot-Contract |
| Draft bleibt live veraenderlich | fachlich gewollt, aber ueberraschend | Aenderungs-/Nicht-verfuegbar-Hinweise |
| Finalisierung zu leicht rueckgaengig | Historie verliert Verlaesslichkeit | keine Entsperrung, nur neue Version |
| PDF nur reproduzieren | Bytes koennen sich durch Fonts/Renderer aendern | Snapshot und ausgegebenes PDF mit Hash behalten |
| PDF dauerhaft behalten | zusaetzliche sensible Datei | verwalteter studentenzentrierter Pfad und Retention |
| gemeinsame Infrastruktur wird generisch | Fachgrenzen verwischen | nur Dokumenttechnik teilen, Aggregate getrennt halten |
| aktueller Renderer liegt im Prototyp | Produkt-/Packaginggrenze unklar | spaeter kontrolliert in eine produktive Export-Schicht ueberfuehren |
| freie Lehrkraftnamen statt Identitaet | Autorenschaft nicht technisch beweisbar | Anzeigename einfrieren; Benutzer-ID erst mit eigener Identity-Entscheidung |
| LEG speichert zu viele interne Notizen | Datenschutz- und Vertrauensrisiko | finale Fassung auf zweckgebundene Gespraechsergebnisse begrenzen |

## 14. Empfohlene Zielarchitektur

```text
Operative SQLite-Daten
-> Repositories und kanonische Kompetenz-/Evidenzprojektionen
-> domainspezifischer Draft-Composer
-> Berichtsdraft oder LEG-Draft
-> gemeinsamer Snapshot-/Render-Contract
-> Finalisierungsservice der jeweiligen Domain
-> unveraenderliche Berichtsversion oder LEG-Version
-> Qt-Vorschau / PDF-Renderer
-> registriertes Exportartefakt
```

Verantwortlichkeiten:

- **Repositories:** lesen und schreiben ihre jeweilige Draft-/Versionsdomain; keine UI-Logik.
- **Kanonische Projektionen:** bleiben einzige Quelle fuer aktuelle Kompetenzstaende und Evidenz.
- **Draft-Composer:** verbindet gespeicherte manuelle Inhalte und Referenzen mit Live-Daten; markiert Veraenderungen und Ausfaelle.
- **Finalisierungsservice:** validiert Pflichtinhalt und Referenzen, erzeugt den domainspezifischen Snapshot, berechnet den Hash und sperrt die Version transaktional.
- **Snapshot-/Render-Contract:** ist versioniert, unveraenderlich und vollstaendig fuer Darstellung/Export.
- **Qt-Vorschau:** rendert nur das Render-Modell und schreibt keine Fachinformationen.
- **PDF-Renderer:** rendert nur das Render-Modell und kennt keine Produktdatenbank.
- **Artefaktservice:** verwaltet Pfad, Dateiname, Hash, Renderer-Metadaten und erneute Exporte.

Bericht und LEG erhalten getrennte Commands, Services, Repositories, Validatoren und Statusregeln. Gemeinsam genutzt werden unveraenderliche Infrastrukturbausteine; es gibt keine abstrakte Universal-Workflow-Engine.

## 15. Umsetzungsschnitte fuer folgende Sprints

### Folgesprint 1: Product Decision und Governance Freeze

- die fuenf Entscheidungen aus Abschnitt 16 treffen
- bestehende Dokumente in der vorgeschriebenen Reihenfolge aktualisieren
- technische Namen, Datenquellen, Lifecycles, Ownership und UI-Mapping registrieren
- Snapshot- und Render-Contract als reviewbares Schema definieren
- keine UI-Implementierung vor Freigabe

### Folgesprint 2: Additive Versions- und Snapshotbasis

- Bericht-/LEG-Aggregate und Versionen additiv modellieren
- Migration fuer bestehende Drafts implementieren
- Revision, Unveraenderlichkeit, Hash und Rollbackpfad testen
- noch keine Finalisierungs-UI und kein PDF-Artefaktmanagement

### Folgesprint 3: Bericht finalisieren und korrigieren

- Berichtsdraft auf neue Versionbasis umstellen
- Finalisierungsvalidator, Snapshot und Schreibschutz
- historische Fassung und Korrektur als neue Version
- bestehende Live-Berichtsvorschau klar von der Berichtswerkstatt abgrenzen

### Folgesprint 4: Gemeinsames Vorschau-/PDF-Modell und Artefakte

- Qt-Vorschau auf dasselbe Render-Modell wie PDF umstellen
- Renderer aus dem Prototyp-Pfad in freigegebene produktive Export-Schicht ueberfuehren
- studentenzentrierte Ablage, Dateinamen, Hash, Artefaktmetadaten und Neuerzeugung
- Layout-, Font-, Seitenumbruch- und Reproduzierbarkeitstests

### Folgesprint 5: LEG abschliessen, korrigieren und Folgegespraech

- datensparsamen LEG-Abschlusssnapshot umsetzen
- Schreibschutz, historische Fassung und Korrekturversion
- Folgegespraech als neue fachliche Identitaet
- optionalen LEG-Export nur nach eigener Freigabe

Jeder Schnitt benoetigt Technical Review, fokussierte Tests, Gesamtregression und einen selektiven Commit. Eine Schema-, UI- oder Exportfreigabe darf nicht aus diesem Vorschlag abgeleitet werden.

## 16. Offene Product-Owner-Entscheidungen

### 1. Wer darf finalisieren beziehungsweise abschliessen?

**Empfohlene Option:** Im ersten lokalen Produktumfang finalisiert die verantwortliche Lehrkraft selbst nach expliziter Pruefansicht; der Anzeigename und Zeitpunkt werden eingefroren. Es gibt noch keinen kuenstlichen `reviewed`-Status ohne Benutzer-/Rollenmodell.

**Alternative:** Vier-Augen-Freigabe mit Ersteller und pruefender/freigebender Person.

**Konkrete Auswirkung:** Die Alternative erfordert vor der Berichtsversionierung eine eigene Benutzer-, Rollen- und Berechtigungsdomain sowie zusaetzliche Statuswechsel.

### 2. Welcher Berichtstyp und Zeitraum gehoeren in den ersten finalen Umfang?

**Empfohlene Option:** Ausschliesslich `learning_development` mit explizitem Beginn und Ende; kein automatisch behauptetes Schuljahr und keine weiteren Zeugnis-/Jahresberichtstypen.

**Alternative:** Mehrere feste Berichtstypen mit schuljahres- oder halbjahresbezogenen Pflichtzeiträumen.

**Konkrete Auswirkung:** Die Alternative erweitert Validierung, Pflichtfelder, Vorlagen, Migration und PDF-Layout deutlich und muss vor dem Snapshot-Schema feststehen.

### 3. Welche LEG-Inhalte werden beim Abschluss dauerhaft eingefroren?

**Empfohlene Option:** Gespraechsrahmen, bewusst ausgewaehlte Kompetenzen/Belege, gemeinsam vereinbarte Ziele, Unterstuetzung, Vereinbarungen, Zustaendigkeiten und Ueberpruefungstermin. Reine interne Vorbereitung bleibt Draft-Inhalt und wird nicht automatisch Teil der Abschlussfassung.

**Alternative:** Den gesamten Draft einschliesslich interner Lehrkraftvorbereitung einfrieren.

**Konkrete Auswirkung:** Die Alternative vergroessert Datenschutz-, Aufbewahrungs- und Zugriffsrisiken und veraendert die Bedeutung einer spaeteren LEG-Einsicht.

### 4. Wie werden Anhaenge in finalen Fassungen behandelt?

**Empfohlene Option:** Nur explizit einbezogene Anhaenge werden beim Abschluss unveraenderlich in den Versionsordner kopiert und gehasht; alle anderen Dateien bleiben ausschliesslich operativ referenziert.

**Alternative:** Nur Referenzen speichern und auf die operative Datei vertrauen.

**Konkrete Auswirkung:** Die Alternative spart Speicherplatz, kann aber eine historische Fassung nach Entfernen oder Ersetzen der Datei unvollstaendig machen.

### 5. Werden ausgegebene finale PDFs dauerhaft archiviert?

**Empfohlene Option:** Ja. Snapshot und jede tatsaechlich ausgegebene finale PDF werden mit eigenem Hash behalten; erneute Exporte erzeugen neue Artefakte und ueberschreiben nichts.

**Alternative:** Nur den Snapshot speichern und PDFs bei Bedarf neu rendern.

**Konkrete Auswirkung:** Die Alternative spart Dateien, kann aber wegen geaenderter Renderer, Fonts oder Templates nicht garantieren, dass spaeter exakt dieselben PDF-Bytes erneut entstehen.
