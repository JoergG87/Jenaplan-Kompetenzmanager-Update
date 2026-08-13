# LEG UX Audit und Zielbild

Status: verbindliches UX-Zielbild fuer UI-Sprint 6B, fortgeschrieben fuer den Qt-Pilotabschluss

Stand: 2026-08-12

## 1. Executive Summary

Der produktive LEG-Pfad ist fachlich tragfaehig: Ein `LearningConferenceDraft` wird ueber ViewModel, Desktop-Adapter, Application Service, Domain Service und Repository atomar in SQLite gespeichert. Manuelle Texte, Gespraechsrahmen sowie bewusst ausgewaehlte Fach-, Themen-, Kompetenz-, Beobachtungs- und Diagrammreferenzen werden vollstaendig wiederhergestellt. Historische Kompetenzreferenzen bleiben lesbar; spaeter nicht mehr verfuegbare Beobachtungen bleiben als neutrale Referenz erhalten. Der LEG-Draft veraendert weder Beobachtungen noch die kanonische Kompetenzstatus-Projektion.

Das Hauptproblem ist die heutige Interaktionsarchitektur. Die sechs Gespraechsphasen sind keine navigierbaren Arbeitsschritte, sondern sechs fortlaufende, read-only Vorschauabschnitte in der rechten Spalte. Alle Eingaben liegen in einer sehr langen linken Spalte unter `Vorbereitung der Lehrkraft` – einschliesslich der Felder fuer gemeinsam vereinbarte Ergebnisse. Dadurch sind Vorbereitung, Gespraechsnotiz und Vereinbarung technisch getrennt gespeichert, visuell aber nicht am Ort ihrer Verwendung getrennt. Der rechte Bereich sieht wie die eigentliche Gespraechsmappe aus, ist jedoch nicht editierbar.

UI-Sprint 6B soll deshalb keinen weiteren Vorschau- oder Dokumentworkflow bauen, sondern den vorhandenen Draft als phasenorientierten Arbeitsraum neu komponieren:

- stabiler Kind- und Gespraechskontext im Kopf,
- kompakte linke Ankerleiste mit allen sechs bestehenden Inhalten in den drei sichtbaren Arbeitskontexten `Vorbereitung`, `Im Gespräch` und `Vereinbarungen & Abschluss`,
- genau ein aktiver, direkt waehlbarer Inhaltsanker mit grosszuegigem Schreibraum,
- in jeder Phase klar markierte Bereiche `Vorbereitung der Lehrkraft`, `Im Gespraech bearbeiten` und – nur wo fachlich vorhanden – `Als Vereinbarung festgehalten`,
- Kompetenz- und Belegauswahl konzentriert im Vorbereitungsanker `evidence`, sichtbar `Vorbereiten · im Gespräch bei Bedarf`,
- kontextuelle, read-only Zusammenfassung ausgewaehlter Belege in den anderen Phasen,
- persistente untere Aktionsleiste mit `Entwurf speichern` als einziger persistierender Primaeraktion,
- lokaler, nicht persistierter Hinweis auf ungespeicherte Aenderungen,
- keine Abschluss-, Revisions-, Snapshot-, PDF- oder Exportdarstellung.

Verbindlich ist eine kompakte linke Ankernavigation als Kombination aus Uebersicht und direkter Wahl. Ein horizontales SegmentedControl ist fuer sechs lange Titel bei 1180 x 760 ungeeignet. Die Leiste zeigt `Aktuell`, `Inhalt vorhanden` oder `Noch leer`, niemals Nummern, `abgeschlossen`, Prozentwerte oder Haken. Die sichtbaren Gruppen sind reine Orientierung und keine zusaetzlichen Seiten.

## 2. Aktueller Arbeitsablauf

Der heutige Weg lautet:

```text
Schuelerprofil
-> Weitere Aktionen
-> Lernentwicklungsgespraech
-> Shell listet Drafts des Kindes
-> kein Draft: neuer lokaler Entwurf
-> genau ein Draft: direkt oeffnen
-> mehrere Drafts: QInputDialog-Auswahl oder neuen Entwurf anlegen
-> Live-Vorbereitung aus Schueler-, Kompetenzstatus- und Beobachtungsprojektion
-> LearningConferenceDialog
-> Entwurf speichern
-> Desktop-Adapter
-> Application Service
-> Domain Service und Validierung
-> SQLiteLearningConferenceDraftRepository
-> SQLite
```

Der Dialog zeigt zwei gleichzeitig sichtbare und getrennt scrollbare Spalten:

1. links `Vorbereitung der Lehrkraft` mit Gespraechsrahmen, Schwerpunktwahl, Kompetenz- und Belegauswahl, allen Textfeldern, Diagrammauswahl und vereinbarten Ergebnissen;
2. rechts eine live neu aufgebaute `Gespraechsmappe` mit sechs nummerierten, nicht editierbaren Abschnitten.

Jede Eingabe links startet nach 60 ms einen Neuaufbau der rechten Projektion. Der Zustand der rechten Seite ist keine eigene Datenquelle und wird nicht gespeichert. Die sichtbaren Phasen besitzen keine technischen Phase-IDs, keinen gespeicherten Phasenstatus und keinen Abschlusszustand.

Der Profilzugang ist vorhanden, aber unter `Weitere Aktionen` wenig auffaellig. Bei mehreren Drafts zeigt der einfache Auswahldialog Datum beziehungsweise Zeitraum, Lehrkraft und technische `LCD`-ID. Er unterstuetzt die Wiederaufnahme funktional, wirkt jedoch eher technisch als paedagogisch.

## 3. Bestehende sechs Phasen

Die implementierten und fuer UI-Sprint 6B massgeblichen Phasen sind:

| Nr. | Sichtbarer Titel | Heutiger Inhalt | Technische Quelle |
| --- | --- | --- | --- |
| 1 | Gespraechsziel | Gespraechseinstieg und ausgewaehlte Fach-/Querschnittsbereiche | `conversation_entry_text`, `subject_ids`, `cross_topic_keys` |
| 2 | Was gelingt dem Kind? | Rueckblick des Kindes und Staerken | `child_retrospective_text`, `strengths_text` |
| 3 | Welche Entwicklung sehen wir? | Sicht der Lehrkraft und Entwicklungsfelder | `teacher_perspective_text`, `development_fields_text` |
| 4 | Woran moechten wir gemeinsam arbeiten? | vorbereitete Ziele | `prepared_goals_text` |
| 5 | Welche Beispiele stuetzen unsere Einschaetzung? | ausgewaehlte Kompetenzen, Beobachtungsbelege und optionale Gespraechsbilder | `competency_ids`, `observation_ids`, `chart_types` plus Live-Projektionen |
| 6 | Welche Unterstuetzung und Vereinbarungen treffen wir? | vorbereitete Unterstuetzung/Vereinbarungen sowie gemeinsam vereinbarte Ziele, Unterstuetzung, Vereinbarungen, Zustaendigkeiten und Ueberpruefungstermin | `prepared_support_text`, `prepared_agreements_text`, `agreed_goals_text`, `agreed_support_text`, `agreed_agreements_text`, `responsibilities_text`, `next_review_date` |

Die alternativ gepruefte Struktur `Gespraech vorbereiten` bis `Abschluss und naechster Blick` wird fuer UI-Sprint 6B nicht uebernommen. Sie wuerde die bestehenden Phasen umbenennen, Phase 2 bis 4 neu zuschneiden und mit `Abschluss` eine nicht vorhandene Finalitaet nahelegen. Eine spaetere Umbenennung braeuchte mindestens neue sichtbare Zuordnungen, aktualisierte UI-Tests, Accessible Names, Hilfetexte und eine Product-Owner-Freigabe. Sie benoetigt keine Schemaaenderung, ist aber mehr als ein Layoutwechsel.

## 4. Aktuelle Informationsarchitektur

### Dauerhafter Kontext heute

Im oberen Dialogbalken stehen Produkttitel, allgemeine Arbeitsbeschreibung, Speichertext, `Entwurf speichern` und `Schliessen`. Kind, Stammgruppe, Zeitraum, Gespraechsdatum und Lehrkraft stehen erst innerhalb der linken Scrollspalte. In der rechten Hero-Karte werden Stammgruppe, Zeitraum, Datum und Lehrkraft wiederholt. Der Kurs wird im LEG-ViewModel heute nicht mitgefuehrt, obwohl er in der vorhandenen Schuelerprojektion vorliegt.

### Vorbereitung der Lehrkraft heute

Als Vorbereitung erscheinen Zeitraum, Gespraechsdatum und Lehrkraft; Fachbereiche und Querschnittsthemen; Kompetenzen mit kanonischem Dokumentationsstand; Beobachtungsbelege; Gespraechseinstieg; Rueckblick des Kindes; Sicht der Lehrkraft; Staerken und Entwicklungsfelder; vorbereitete Ziele, Unterstuetzung und Vereinbarungen sowie optionale Diagrammtypen.

Die Karte `Gespraechsleitfaden` bezeichnet alle acht dort enthaltenen Textfelder pauschal als Vorbereitung der Lehrkraft. Besonders bei `Rueckblick des Kindes` ist die beabsichtigte Autorenschaft dadurch unklar.

### Gemeinsam bearbeitete und vereinbarte Inhalte heute

Die Felder `agreed_goals_text`, `agreed_support_text`, `agreed_agreements_text`, `responsibilities_text` und `next_review_date` liegen in einer eigenen Karte `Im Gespraech gemeinsam vereinbart`. Diese fachlich richtige Trennung wird jedoch geschwaecht, weil die Karte weiterhin in der linken Gesamtspalte unter der Hauptueberschrift `Vorbereitung der Lehrkraft` steht.

### Live-Projektion heute

Die rechte Gespraechsmappe ist vollstaendig read-only. Sie zeigt die Eingaben in phasenartiger Reihenfolge, bietet aber weder Navigation noch direkte Bearbeitung. Vorbereitung, Live-Gespraech und Ergebnis werden somit als Vorschau komponiert, nicht als eigentlicher Arbeitsfluss.

## 5. Wichtigste UX-Probleme

1. **Phasen sind nur Darstellung.** Die Nummern 01 bis 06 sehen nach Ablauf aus, koennen aber nicht angesteuert werden. Der schnelle Wechsel zu Zielen oder Vereinbarungen ist nur ueber langes Scrollen links moeglich.
2. **Eingaben stehen am falschen Ort.** Gemeinsam vereinbarte Felder liegen unter `Vorbereitung der Lehrkraft`; der sichtbar als Gespraechsmappe bezeichnete Bereich ist nicht editierbar.
3. **Extrem lange Vorbereitungsspalte.** In einer repraesentativen Offscreen-Pruefung mit 11 Faechern und 40 Beobachtungen betrug der vertikale Scrollweg links selbst bei 1400 x 900 rund 3386 px, bei 1280 x 800 rund 3486 px und bei 1200 x 760 rund 3526 px.
4. **1180 x 760 ist technisch nicht erreichbar.** Der Dialog besitzt `setMinimumSize(1200, 760)`. Eine angeforderte Breite von 1180 px wird auf 1200 px angehoben.
5. **Zu wenig Schreibraum.** Acht vorbereitete und vier gemeinsam vereinbarte Textfelder haben jeweils nur 82 px Mindesthoehe und teilen sich die linke Spalte mit allen Auswahlbereichen.
6. **Doppelte Wahrnehmung.** Texte werden links editiert und rechts gleichzeitig als Vorschau wiederholt. Das erhoeht die visuelle Dichte, ohne einen zweiten fachlichen Nutzen zu schaffen.
7. **Feldzuordnung ist teilweise unklar.** `Gespraechseinstieg` erscheint rechts unter `Gespraechsziel`; `Rueckblick des Kindes` steht unter Lehrkraftvorbereitung; `Gemeinsam vereinbarte Ziele` erscheinen erst in Phase 6 statt neben den vorbereiteten Zielen in Phase 4.
8. **Vereinbarungslabels sind sprachlich schwer.** `Vorbereitete Vereinbarungen` und `Gemeinsam vereinbarte Vereinbarungen` sind korrekt getrennte Felder, aber in direkter Folge sprachlich redundant.
9. **Optionaler Ueberpruefungstermin wirkt verpflichtend.** Das Domainfeld ist optional, die UI setzt fuer neue Drafts jedoch automatisch das heutige Datum und bietet keinen leeren Zustand.
10. **Speicherstatus ist nicht belastbar sichtbar.** Nach dem Speichern bleibt `Entwurf gespeichert` auch nach weiteren Aenderungen stehen. Ein Dirty-State fehlt; der ISO-/UTC-Zeitstempel ist nicht lesefreundlich lokalisiert.
11. **Schliessen verwirft still.** Es gibt kein Autosave und keine Warnung bei ungespeicherten Aenderungen.
12. **Validierung unterbricht den Fluss.** Domainfehler erscheinen in einer modalen `QMessageBox`, nicht als `InlineMessage` nahe der persistenten Aktion.
13. **Belegfunktionen sind schwer auffindbar.** Dokumentationsfilter, Erhalt historischer Auswahl, neutrale Mengenwarnung und reine Textnutzung von Schnellbeobachtungen sind vorhanden, liegen aber tief in der langen Spalte.
14. **Querschnittsthemen filtern Belege nur unvollstaendig.** Beobachtungen besitzen im LEG-ViewModel Fachname und Kompetenz-IDs, aber keine Zuordnung zu den vier Querschnittsthemen. Die Themen steuern Gespraechsfokus und Anzeige, koennen allein jedoch keine passend markierten Beobachtungen liefern.
15. **Diagrammauswahl und sichtbares Ergebnis koennen auseinanderfallen.** Ein Diagrammtyp kann gespeichert sein, obwohl die aktuelle Auswahl fuer seine Darstellung keine Kompetenz- oder datierten Beobachtungsbelege liefert.
16. **Einstieg ist technisch.** Bei mehreren Drafts dominiert ein Standard-Auswahldialog mit `LCD`-ID. Im Profil ist das LEG nur im Menue `Weitere Aktionen` zu finden.
17. **Testdaten decken Wiederaufnahme nicht realistisch ab.** Die fokussierten Tests erzeugen vollstaendige Drafts, der produktionsnahe Pilot-Seed legt jedoch keinen LEG-Draft an. Die aktuelle lokale Baseline enthielt beim Audit ebenfalls keinen LEG-Draft.

Kein aktuelles Element bietet einen Button `Abschliessen` oder `Finalisieren`. Potenziell final wirkend sind dennoch die Begriffe `Gespraechsmappe`, `Im Gespraech gemeinsam vereinbart` und die nummerierte lineare Darstellung, wenn Speicher- und Draftstatus nicht im gleichen Blickfeld bleiben. Das Zielbild muss deshalb `Bearbeitbarer Entwurf` dauerhaft sichtbar halten.

## 6. Vorbereitung versus Gespraech versus Vereinbarung

UI-Sprint 6B verwendet drei sichtbare Inhaltsrollen. Sie sind reine UX-Gruppierungen und fuehren keinen neuen fachlichen Status ein.

| Rolle | Bedeutung | Bestehende Felder/Inhalte | Darstellung |
| --- | --- | --- | --- |
| Vorbereitung der Lehrkraft | interne, vor dem Gespraech formulierte Orientierung | `conversation_entry_text`, `teacher_perspective_text`, `strengths_text`, `prepared_goals_text`, `prepared_support_text`, `prepared_agreements_text`; kanonischer Kompetenzstand als read-only Kontext | ruhige `AppCard[soft]`, Label `Nur fuer die Vorbereitung` |
| Im Gespraech bearbeiten | gemeinsam besprochene oder im Gespraech erfasste Inhalte, noch ohne Abschlusssemantik | `child_retrospective_text`, `development_fields_text`; bewusste Belegbetrachtung | normale Schreibflaeche, Label `Im Gespraech bearbeiten` |
| Als Vereinbarung festgehalten | im bearbeitbaren Draft ausdruecklich als gemeinsam vereinbart gespeicherte Texte | `agreed_goals_text`, `agreed_support_text`, `agreed_agreements_text`, `responsibilities_text`, `next_review_date` | `AppCard[accent]` sparsam, Label `Im Entwurf als Vereinbarung festgehalten` |

Die dritte Rolle bedeutet nicht final, freigegeben, unterschrieben oder unveraenderlich. Der genaue Wortlaut `Im Entwurf als Vereinbarung festgehalten` soll diese Grenze sichtbar machen.

Die Zuordnung der nicht mit `prepared_` oder `agreed_` praefigierten Felder ist im Code nicht vollstaendig fachlich entschieden. Das Zielbild empfiehlt die obige Zuordnung, weil sie den sichtbaren Titeln und der Gespraechssituation am besten entspricht. Sie veraendert weder Feldnamen noch Persistenz.

## 7. Zielbild des LEG-Workspace

### 7.1 Grundaufbau

```text
Stabiler Kopf
  Kind | Stammgruppe / Kurs | Gespraechsdatum | Lehrkraft
  aktueller Arbeitskontext und Anker | Bearbeitbarer Entwurf | Speicherstatus

Arbeitsflaeche
  kompakte linke Ankerleiste mit drei sichtbaren Gruppen
  aktiver Inhaltsanker mit Schreib- und Auswahlbereich
  kontextuelle Auswahlzusammenfassung ab 1280 px

Persistente Aktionsleiste
  Schliessen/Abbrechen | Belege ansehen bei Bedarf | Entwurf speichern
```

Der Kopf bleibt ausserhalb aller Scrollbereiche. Er zeigt Kind, Stammgruppe und – nach kleiner Erweiterung der bestehenden Live-Projektion – Kurs, ausserdem Gespraechsdatum, verantwortliche Lehrkraft, aktuellen Arbeitskontext mit Ankertitel und Speicherstatus. Datum und Lehrkraft werden unter `Gesprächsziel` bearbeitet und im Kopf nur gespiegelt.

Die Mitte zeigt immer genau einen der sechs Inhaltsanker. Vorbereitung und gemeinsam bearbeitete Inhalte stehen innerhalb desselben Ankers nebeneinander oder untereinander und tragen eindeutige Rollenlabels. Der bisherige permanente zweite Vorschau-Scrollbereich entfaellt. Eine kompakte Zusammenfassung ausgewaehlter Bereiche und Belege bleibt als Kontext verfuegbar, ist ausserhalb von `evidence` jedoch read-only.

Die untere Aktionsleiste bleibt immer sichtbar. `Entwurf speichern` ist rechts die einzige blaue und einzige persistierende Hauptaktion. Phasenwechsel veraendert nur lokalen UI-State und speichert nicht automatisch.

### 7.2 Inhaltsstatus ohne Fortschrittsbehauptung

Jede Ankerzeile zeigt genau einen der folgenden textlichen Zustaende:

- `Aktuell`,
- `Inhalt vorhanden`,
- `Noch leer`.

Die Kennzeichnung wird nur aus dem aktuellen Widget-/Draftinhalt abgeleitet und nicht gespeichert. Es gibt keine Nummerierung, Haken, Prozentanzeige, Pflichtquote, Sperre, Erfolgsfarbe oder Bezeichnung `fertig`/`abgeschlossen`. Alle Anker bleiben jederzeit direkt erreichbar.

### 7.3 Wiederaufnahme

Beim Wiedereroeffnen werden alle gespeicherten Draftfelder und Auswahlreferenzen rekonstruiert. UI-Sprint 6B verspricht bewusst nicht die Wiederherstellung des zuletzt aktiven Ankers, weil dafuer kein persistiertes Feld existiert und keine neue Datenquelle eingefuehrt werden soll. Ein wiedereroeffneter Draft startet deterministisch bei `Gesprächsziel`; die Ankerleiste zeigt sofort, wo bereits Inhalt vorhanden ist, und erlaubt direkten Wechsel.

Der Kopf zeigt `Zuletzt gespeichert: TT.MM.JJJJ, HH:MM`. Nach einer Aenderung wechselt die lokale Anzeige unmittelbar zu `Ungespeicherte Aenderungen`. Dieser Dirty-State ist fluechtig und kein Domainstatus.

## 8. Verbindliche gruppierte Ankernavigation

Verwendet wird eine **kompakte linke Ankernavigation mit drei sichtbaren Arbeitskontexten und sechs direkten Zielen**.

| Variante | Bewertung | Entscheidung |
| --- | --- | --- |
| Horizontales SegmentedControl | Die sechs langen Titel benoetigen bei 1180 px zu viel Breite, brechen unruhig oder werden unverstaendlich gekuerzt. Pfeiltasten waeren gut, die Lesbarkeit nicht. | nicht verwenden |
| Vertikale Schrittleiste | Gute Lesbarkeit und direkter Wechsel, kann mit Haken/Verbindungslinie aber ungewollt Abschluss suggerieren. | nur ohne Stepper-/Completion-Semantik |
| Kompakte linke Ankernavigation | Alle Titel koennen zweizeilig umbrechen; aktueller Anker, vorhandener Inhalt und leere Anker sind gleichzeitig sichtbar; schnelle Maus- und Tastaturnavigation. | verwenden |
| Separate Uebersicht plus aktueller Schritt | Zusaetzlicher Modus erhoeht Navigation und nimmt Schreibraum. | nicht als eigene Seite; die linke Leiste ist bereits die Uebersicht |

Verbindliche Eigenschaften:

- Breite 220 bis 236 px; bei 1180 px maximal 210 bis 220 px.
- Vollstaendige Phasentitel mit Zeilenumbruch; keine abgeschnittenen Titel.
- Aktueller Anker durch Form, Schriftgewicht, linken Marker und Text `Aktuell`, nicht nur durch Farbe.
- `Inhalt vorhanden` und `Noch leer` als kleine textliche Unterzeile.
- Drei sichtbare Gruppen ohne eigene Seite: `Vorbereitung` (`goal`, `evidence`), `Im Gespräch` (`strengths`, `development`) und `Vereinbarungen & Abschluss` (`goals`, `agreements`).
- Direktwahl jedes Ankers per Klick sowie Enter/Space.
- Pfeil hoch/runter wechselt den fokussierten Anker in sichtbarer Gruppenreihenfolge, Home/End springt zum ersten/letzten Anker.
- Ankerwechsel ist sofort, ohne Speichern und ohne Finalitaet; lineare Aktionen `Zurück` und `Weiter` entfallen.
- Fokus wechselt nach Aktivierung auf die Ankerueberschrift beziehungsweise erste sinnvolle Eingabe.

## 9. Zielstruktur der sechs Inhaltsanker

### Anker `goal` – Gespraechsziel

- **Zweck:** Gespraechsrahmen und bewusste Schwerpunkte festlegen.
- **Sichtbarer Kontext:** Kind, Stammgruppe/Kurs, Draftstatus, Zeitraum, Gespraechsdatum, Lehrkraft.
- **Eingaben:** Zeitraum, Gespraechsdatum, verantwortliche Lehrkraft, Fachbereiche, Querschnittsthemen, vorbereiteter Gespraechseinstieg.
- **Vorbereitete Informationen:** Live-Kindkontext; kurze Erklaerung, dass der Zeitraum die Belegauswahl filtert.
- **Gemeinsam bearbeitete Inhalte:** keine neue fachliche Eingabe; ausgewaehlte Bereiche werden als Gespraechsfokus gezeigt.
- **Gespeicherte Ergebnisse:** `period_start`, `period_end`, `conference_date`, `responsible_teacher`, `subject_ids`, `cross_topic_keys`, `conversation_entry_text`.
- **Primaere Aktion:** `Entwurf speichern` in der globalen Leiste.
- **Sekundaere Aktionen:** direkte Ankerwahl, Schwerpunkte aendern, Schliessen/Abbrechen.
- **Hilfetext:** `Der Zeitraum grenzt sichtbare Kompetenzbelege ein; das Gespraechsdatum bezeichnet den Termin.`
- **Leerzustand:** `Noch keine Gespraechsschwerpunkte ausgewaehlt. Du kannst den Entwurf trotzdem speichern.`

### Anker `strengths` – Was gelingt dem Kind?

- **Zweck:** Staerken vorbereiten und die Perspektive des Kindes im Gespraech festhalten.
- **Sichtbarer Kontext:** ausgewaehlte Bereiche und kompakte read-only Belegzusammenfassung.
- **Eingaben:** `strengths_text` unter `Nur fuer die Vorbereitung`; `child_retrospective_text` unter `Im Gespraech bearbeiten`.
- **Vorbereitete Informationen:** ausgewaehlte, passende Kompetenz- und Beobachtungsbelege als aufklappbarer Kontext; keine Textvorschlaege.
- **Gemeinsam bearbeitete Inhalte:** Rueckblick des Kindes.
- **Gespeicherte Ergebnisse:** `strengths_text`, `child_retrospective_text`.
- **Primaere Aktion:** `Entwurf speichern`.
- **Sekundaere Aktionen:** direkte Ankerwahl, `Belege ansehen`.
- **Hilfetext:** `Belege dienen als Erinnerung. Die paedagogische Formulierung entsteht durch die Lehrkraft und im Gespraech.`
- **Leerzustand:** getrennt `Noch keine vorbereiteten Staerken notiert` und `Rueckblick wird im Gespraech ergaenzt`.

### Anker `development` – Welche Entwicklung sehen wir?

- **Zweck:** Lehrkraftperspektive und gemeinsam betrachtete Entwicklungsfelder unterscheiden.
- **Sichtbarer Kontext:** relevante Kompetenzstaende und datierte Belege read-only, historische Kennzeichnung eingeschlossen.
- **Eingaben:** `teacher_perspective_text` unter `Nur fuer die Vorbereitung`; `development_fields_text` unter `Im Gespraech bearbeiten`.
- **Vorbereitete Informationen:** kanonischer Dokumentationsstand und ausgewaehlte Belege ohne automatische Interpretation.
- **Gemeinsam bearbeitete Inhalte:** Entwicklungsfelder als manuelle Gespraechsnotiz.
- **Gespeicherte Ergebnisse:** `teacher_perspective_text`, `development_fields_text`.
- **Primaere Aktion:** `Entwurf speichern`.
- **Sekundaere Aktionen:** direkte Ankerwahl, Kontext ein-/ausblenden.
- **Hilfetext:** `Der angezeigte Stand ist Dokumentationskontext, keine automatische paedagogische Einschaetzung.`
- **Leerzustand:** `Noch keine Lehrkraftperspektive vorbereitet` beziehungsweise `Noch keine Entwicklungsfelder notiert`.

### Anker `goals` – Woran moechten wir gemeinsam arbeiten?

- **Zweck:** vorbereitete Zielideen von im Gespraech vereinbarten Zielen trennen.
- **Sichtbarer Kontext:** Staerken, Entwicklungsfelder und ausgewaehlte Belege als kurze Zusammenfassung.
- **Eingaben:** `prepared_goals_text` unter `Nur fuer die Vorbereitung`; `agreed_goals_text` unter `Im Entwurf als Vereinbarung festgehalten`.
- **Vorbereitete Informationen:** manuell formulierte Zielideen; keine automatische Ableitung.
- **Gemeinsam bearbeitete Inhalte:** gemeinsame Zielformulierung.
- **Gespeicherte Ergebnisse:** `prepared_goals_text`, `agreed_goals_text`.
- **Primaere Aktion:** `Entwurf speichern`.
- **Sekundaere Aktionen:** direkte Ankerwahl, Belege ansehen.
- **Hilfetext:** `Vorbereitete Ideen werden nicht automatisch zu Vereinbarungen.`
- **Leerzustand:** je Rolle ein eigener neutraler Leerzustand.

Die sichtbare Verschiebung von `agreed_goals_text` aus der heutigen Phase 6 in Phase 4 ist die einzige empfohlene Neuzuordnung eines bereits vorhandenen Feldes. Sie aendert keine Persistenz, muss aber in UI-Tests, Mapping und Hilfetexten nachvollzogen werden.

### Anker `evidence` – Welche Beispiele stuetzen unsere Einschaetzung?

- **Zweck:** Fachbereiche, konkrete Kompetenzen, Beobachtungen und optionale Darstellungen bewusst fuer das Gespraech auswaehlen.
- **Sichtbarer Kontext:** Zeitraum, ausgewaehlte Bereiche, Auswahlzaehler und historische/nicht verfuegbare Referenzen.
- **Eingaben:** `competency_ids`, `observation_ids`, `chart_types`; Fach-/Querschnittsauswahl bleibt aus Phase 1 sichtbar, aber wird dort bearbeitet.
- **Vorbereitete Informationen:** Hierarchie Fach -> Kompetenzbereich -> Thema -> Kompetenz, kanonischer Status, Beobachtungsdatum, Kontext, Notiz und Schnellbeobachtungskennzeichnung.
- **Gemeinsam bearbeitete Inhalte:** keine automatisch erzeugte Aussage; Belege koennen im Gespraech betrachtet werden.
- **Gespeicherte Ergebnisse:** ausschliesslich Auswahlreferenzen und Diagrammtypen.
- **Primaere Aktion:** `Entwurf speichern`.
- **Sekundaere Aktionen:** Suche leeren, Auswahl anzeigen, direkte Ankerwahl.
- **Hilfetext:** `Die Auswahl legt Gespraechsbelege fest. Sie bewertet oder interpretiert sie nicht.`
- **Leerzustand:** pro Fach `In diesem Zeitraum sind noch keine kompetenzbezogenen Beobachtungen dokumentiert`; fuer Belege `Noch keine Beispiele ausgewaehlt`.

### Anker `agreements` – Welche Unterstuetzung und Vereinbarungen treffen wir?

- **Zweck:** vorbereitete Unterstuetzungsideen und Vereinbarungsentwuerfe klar von gemeinsam festgehaltenen Ergebnissen trennen.
- **Sichtbarer Kontext:** Kind, Ziele aus Phase 4, ausgewaehlte Belege, Draftstatus.
- **Eingaben Vorbereitung:** `prepared_support_text`, `prepared_agreements_text`.
- **Eingaben Vereinbarung:** `agreed_support_text`, `agreed_agreements_text`, `responsibilities_text`, optionaler `next_review_date`.
- **Vorbereitete Informationen:** vorbereitete Unterstuetzung und Vereinbarungsentwuerfe.
- **Gemeinsam bearbeitete Inhalte:** Unterstuetzung, Vereinbarung und Zustaendigkeiten.
- **Gespeicherte Ergebnisse:** alle genannten Felder; der gemeinsam vereinbarte Zieltext bleibt sichtbar aus Phase 4.
- **Primaere Aktion:** `Entwurf speichern` – nicht `Abschliessen`.
- **Sekundaere Aktionen:** direkte Ankerwahl, Schliessen.
- **Hilfetext:** `Diese Angaben bleiben Teil eines bearbeitbaren Entwurfs. Sie sind nicht finalisiert oder festgeschrieben.`
- **Leerzustand:** getrennte Leerzustaende fuer Vorbereitung und Vereinbarung; der Ueberpruefungstermin startet leer.

## 10. Kompetenzen und Belege

Die Auswahl wird **innerhalb des Ankers `evidence`** bearbeitet. Damit bleibt sie ein bewusster Vorbereitungsschritt, sichtbar `Vorbereiten · im Gespräch bei Bedarf`, und wird nicht ueber alle Anker als dauerhafte Bearbeitungsflaeche dupliziert. In den anderen Schreibankern erscheint nur eine kompakte, read-only Kontextzusammenfassung mit Aktion `Belege ansehen`, die direkt zu `evidence` wechselt.

Verbindliche Zielstruktur im Anker `evidence`:

1. lokale Suche mit bestehendem `SearchField`;
2. Fachfilter aus Phase 1 als sichtbare Chips;
3. hierarchische Kompetenzliste mit vollstaendig umbrechenden Texten;
4. getrennte Liste `Ausgewaehlt` fuer Kompetenzen und Beobachtungsbelege;
5. optionale, standardmaessig geschlossene Disclosure `Gespraechsbilder`.

Regeln:

- Auswahl bleibt explizit; Filter, Suche und Phasenwechsel loeschen sie nie.
- Nur aktive `current`-Kompetenzen werden neu angeboten.
- Bereits gespeicherte historische/inaktive Kompetenzen bleiben ausgewaehlt und tragen Textkennzeichnung `Historischer Bezug – nicht neu auswaehlbar`.
- Lange Kompetenztexte umbrechen; technische IDs dominieren nicht und stehen nur in Tooltip/Accessible Description.
- Aktive Beobachtungen zeigen Datum, Fach, Kontext und Notiz. Schnellbeobachtungen tragen `Nur als Textbeleg`.
- Spaeter nicht mehr verfuegbare Beobachtungen zeigen neutral `Beleg nicht mehr verfuegbar – gespeicherte Referenz bleibt erhalten`; eine ausdrueckliche Abwahl entfernt nur die Referenz beim naechsten Speichern.
- Keine Beobachtung und kein Kompetenzstand erzeugt automatisch eine paedagogische Aussage.
- Die ruhige Empfehlung `Drei bis fuenf Belege sind meist gut ueberschaubar` bleibt ein Hinweis und veraendert die Auswahl nicht.
- Diagramme sind standardmaessig nicht ausgewaehlt. Nicht darstellbare Diagrammoptionen werden erklaert deaktiviert statt gespeichert, aber unsichtbar nicht gerendert.
- `Dokumentationsabdeckung`, `Kompetenzentwicklung` und `Zeitachse` bleiben dokumentationsbezogen. Symbole erhalten immer Textlegende; Farbe ist nie alleiniger Informationstraeger.

Die Querschnittsthemen haben heute keine technische Belegzuordnung. UI-Sprint 6B darf daher keine vermeintlich automatisch passenden Beobachtungen fuer Arbeitsverhalten, Sozialverhalten, Selbststaendigkeit oder Lernorganisation behaupten. Sie bleiben Gespraechsfokus; Belege werden dazu bewusst manuell ausgewaehlt.

## 11. Schreib- und Vereinbarungsbereiche

Jeder Textbereich verwendet:

- eine klare Rollenueberschrift,
- einen kurzen, nicht wertenden Hilfetext,
- ein mehrzeiliges Eingabefeld mit mindestens 140 px nutzbarer Hoehe auf 1400/1280 und mindestens 120 px auf 1180,
- einen Accessible Name aus Phase, Rolle und Feldzweck,
- keinen automatisch erzeugten Starttext.

| Inhalt | Rolle im Zielbild | Phase |
| --- | --- | --- |
| Gespraechseinstieg | nur fuer Lehrkraft vorbereitet | 1 |
| Staerken | nur fuer Lehrkraft vorbereitet | 2 |
| Rueckblick des Kindes | im Gespraech bearbeiten | 2 |
| Sicht der Lehrkraft | nur fuer Lehrkraft vorbereitet | 3 |
| Entwicklungsfelder | im Gespraech bearbeiten | 3 |
| vorbereitete Ziele | nur fuer Lehrkraft vorbereitet | 4 |
| gemeinsam vereinbarte Ziele | als Vereinbarung im Draft festgehalten | 4 |
| vorbereitete Unterstuetzung | nur fuer Lehrkraft vorbereitet | 6 |
| gemeinsam vereinbarte Unterstuetzung | als Vereinbarung im Draft festgehalten | 6 |
| vorbereitete Vereinbarungen | nur fuer Lehrkraft vorbereitet | 6 |
| gemeinsam vereinbarte Vereinbarungen | als Vereinbarung im Draft festgehalten | 6 |
| Zustaendigkeiten | als Vereinbarung im Draft festgehalten | 6 |
| Ueberpruefungstermin | optionaler Teil der Vereinbarung im Draft | 6 |

Die UI fuehrt keine neue fachliche Statuslogik ein. Die Rollen sind Beschriftung und Layout fuer bereits getrennte Felder. Insbesondere wird `agreed_*` nicht zu `final`, `approved` oder `completed`.

## 12. Aktionshierarchie

Die persistente untere Leiste ist verbindlich:

| Aktion | Rolle | Verhalten |
| --- | --- | --- |
| Entwurf speichern | einzige primaere Aktion | speichert den vollstaendigen aktuellen Draft ueber den bestehenden Pfad |
| Direkte Ankerwahl | lokale Navigation | wechselt nur den sichtbaren Inhalt, speichert nicht und besitzt keine Fortschrittssemantik |
| Schliessen | quiet | schliesst einen bestehenden Draft; bei Dirty-State mit Drei-Wege-Entscheidung `Entwurf speichern`, `Änderungen verwerfen`, `Weiter bearbeiten` |
| Abbrechen | quiet, nur neuer ungespeicherter Draft | verwirft den noch nicht gespeicherten lokalen Zustand nach Bestaetigung, falls Eingaben vorliegen |
| Belege auswaehlen / Belege ansehen | lokale sekundaere Aktion | wechselt zum Anker `evidence`, keine Persistenz |
| Spaeter fortsetzen | kein eigener Button | wird nach erfolgreichem Speichern als Hinweis `Gespeichert – du kannst den Entwurf spaeter fortsetzen` vermittelt |
| Druck / Export | nicht anzeigen | fuer LEG aktuell nicht vorhanden |

`Entwurf speichern` bleibt auch unter `Vereinbarungen & Abschluss` unveraendert. Der Arbeitskontext selbst behauptet keine Finalitaet; Abschluss und Revisionen bleiben getrennte vorhandene Aktionen mit ihren unveraenderten Schutzbedingungen.

Speicherfeedback:

- waehrend des Speicherns Button kurz deaktivieren und `Wird gespeichert ...` anzeigen;
- Erfolg als lokaler Toast plus dauerhaft aktualisierter Speichertext;
- Validierungs- oder Speicherfehler als `InlineMessage` direkt oberhalb der Aktionsleiste, Fokus auf Meldung beziehungsweise betroffenes Feld;
- kein stilles Autosave.

## 13. Motion und Feedback

Das vorhandene zentrale Motion-System reicht aus.

- **Phasenwechsel:** Inhalt sofort wechseln; optional 120 ms Opacity-Bestaetigung des bereits gesetzten Zielschritts. Kein Slide, keine Geometrie- oder Hoehenanimation.
- **InlineMessage:** Erfolgs-/Informationshinweise ruhig einblenden; Warnung und Fehler sofort zeigen.
- **Toast:** nur fuer nicht blockierendes Speicherfeedback; laufende Meldung ersetzen statt stapeln.
- **Disclosure:** Sichtbarkeit sofort setzen, maximal 120 ms Opacity-Bestaetigung. Keine animierten langen Kompetenzlisten.
- **Auswahlfeedback:** nativer Checkbox-/Fokuszustand sofort; kurze zentrale Opacity-Bestaetigung nur bei Bedarf.
- **Dirty-State:** Text und Badge sofort aktualisieren, keine Animation mit Leistungscharakter.

Reduced Motion setzt alle Endzustaende unmittelbar. Timer duerfen die Lesedauer eines Toasts steuern, aber weder Eingabe, Fokus, Auswahl, Speichern noch Navigation verzoegern.

## 14. Responsive Verhalten

### 1400 x 900

- Kopf und Aktionsleiste fest.
- Phasenleiste 230 bis 236 px.
- Haupteditor flexibel, mindestens 640 px.
- Kontextflaeche fuer ausgewaehlte Bereiche/Belege 300 bis 340 px.
- In Phasen 2, 3, 4 und 6 koennen Vorbereitung und Gespraech/Vereinbarung zweispaltig stehen.

### 1280 x 800

- Phasenleiste etwa 220 px.
- Kontextflaeche etwa 280 px und standardmaessig kompakt.
- Schreibkarten duerfen untereinander statt nebeneinander stehen, wenn ein Textfeld sonst unter 420 px Breite faellt.
- Aktionslabels bleiben vollstaendig sichtbar; `Zurück`/`Weiter` werden nicht angezeigt.

### 1180 x 760

- produktives Minimum auf hoechstens 1100 x 720 senken; 1180 x 760 darf nicht auf 1200 px verbreitert werden.
- Phasenleiste 210 bis 220 px.
- keine dauerhafte dritte Spalte; Kontext & Belege erscheinen als statische Inline-Disclosure oberhalb des Schreibbereichs.
- Kopfmetadaten duerfen in zwei Zeilen umbrechen.
- Textfelder stehen einspaltig.
- Aktionsleiste bleibt sichtbar; die direkte Ankerwahl verbleibt in der linken Leiste.

Scrollregel:

- Kopf, Phasenleiste und Aktionsleiste scrollen nicht.
- Normale Phasen besitzen genau einen vertikalen Hauptscrollbereich.
- Der Anker `evidence` nutzt statt eines zusaetzlichen aeusseren Scrollbereichs einen eigenen Listenviewport fuer Kompetenzen/Belege.
- Kein horizontaler Gesamtscroll und kein horizontaler Kompetenzscroll.
- Keine zwei ineinander verschachtelten vertikalen Scrollbereiche unter demselben Mauszeiger.

## 15. Accessibility

- Ankernavigation ist eine eindeutig benannte lokale Navigation `Arbeitsbereiche des Lernentwicklungsgespraechs`.
- Jeder Ankerbutton besitzt vollstaendigen Titel, Arbeitskontext und textlichen Inhaltszustand, aber keine Nummer oder Fortschrittsposition.
- Tab-Reihenfolge: Ankernavigation, aktive Ankerfelder in Lesereihenfolge, Kontext/Belege, lokale Nebenaktionen, Speichern, Schliessen.
- Nach Ankerwechsel liegt der Fokus auf der Ankerueberschrift oder der ersten Eingabe; nach Fehler auf Meldung/Fehlerfeld; nach Speichern bleibt er an der ausloesenden Aktion.
- Enter/Space aktiviert Phase, Disclosure und Auswahl. Pfeile navigieren Phasen und hierarchische Listen gemaess Qt-Konvention.
- Alle Textfelder erhalten Accessible Names mit Arbeitskontext, Ankertitel und Rollenbezug, zum Beispiel `Vereinbarungen & Abschluss, Woran möchten wir gemeinsam arbeiten?, im Entwurf als Vereinbarung festgehalten, Gemeinsam formulierte Ziele`.
- Die vorhandene Domainpflicht bleibt unveraendert: vollstaendiger Zeitraum oder Gespraechsdatum. Der Ueberpruefungstermin ist optional. Lehrkraft wird nicht ohne Fachentscheidung als Pflichtfeld markiert.
- Pflicht und Fehler werden durch Text, Symbol und Fokus vermittelt, nie nur durch Farbe.
- Historisch, nicht verfuegbar, ausgewaehlt und read-only werden jeweils textlich benannt.
- Lange Kompetenztexte und Hilfetexte sind mit Tastatur erreichbar und umbrechen ohne Abschneiden.
- Diagrammsymbole besitzen Textlegende und zugaengliche Beschreibung; eine Grafik ist nie die einzige Aussage.

## 16. Wiederverwendbare Komponenten

Geeignet und ohne Berichtsfunktion zu kopieren sind:

- `PageHeader` fuer Kind- und Gespraechskontext,
- `StatusBadge` fuer `Bearbeitbarer Entwurf` und lokalen Dirty-State,
- `AppCard` mit `default`, `soft` und sparsam `accent` fuer Inhaltsrollen,
- `SectionHeader` fuer Phasenabschnitte und Hilfe,
- `SearchField` fuer Kompetenz- und Belegsuche,
- `FilterBar` und `FilterChip` fuer Zeitraum-/Fachkontext,
- `InlineMessage` fuer Validierung und nicht verfuegbare Referenzen,
- `Toast` fuer Speicherfeedback,
- `EmptyState` fuer leere Phasen und Beleglisten,
- zentrale Buttonrollen und `configure_button`,
- zentrale Motion-Policy und Opacity-Bestaetigung,
- die vorhandene hierarchische Disclosure-Sprache des Kompetenz-Cockpits/Beobachtungsdialogs.

Aus der Berichtswerkstatt eignet sich nur das **Layoutprinzip** einer persistenten Aktionsleiste und eines stabilen Kopfes. Berichtsspezifische Bereiche `Vorschau`, `Revisionen`, Finalisierungsstatus und PDF-Aktionen sind fuer LEG ungeeignet und werden nicht kopiert.

Das bestehende horizontale `SegmentedControl` bleibt fuer kurze lokale Bereiche geeignet, nicht fuer die sechs langen LEG-Phasen.

## 17. Wirklich benoetigte neue Komponenten

Es werden keine neuen globalen Design-System-Komponenten benoetigt. Zwei lokale, klar begrenzte UI-Kompositionen sind fuer UI-Sprint 6B notwendig:

1. **Kompakte LEG-Phasenleiste:** sechs fokussierbare Eintraege, aktueller Schritt, `Inhalt vorhanden`/`Noch leer`, Pfeil-/Home-/End-Navigation. Sie besitzt ausschliesslich lokalen UI-State.
2. **Ruhige Draft-Auswahl beim Einstieg:** fuer mehrere Drafts eine komponierte Liste aus vorhandenen `AppCard`, `StatusBadge` und Buttonrollen mit Gespraechsdatum/Zeitraum, Lehrkraft und zuletzt gespeichert; technische ID nur als Zusatz. Dies ersetzt den generischen `QInputDialog`.

Eine eigene `AgreementCard`, `EvidenceCard`, `PhaseCard`, `ProgressStepper` oder universelle Dokumentkomponente ist nicht gerechtfertigt. Rollenflaechen, Belegzeilen und Aktionsleiste werden aus vorhandenen Komponenten komponiert.

Vor Implementierung muessen konkrete neue technische Namen fuer die beiden lokalen Kompositionen gemaess Projektregel in `docs/TECHNICAL_NAMES.md` registriert werden. Dieses Audit fuehrt bewusst noch keine Implementierungsnamen ein.

## 18. Bewusst unveraenderte Fachlogik

UI-Sprint 6B aendert nicht:

- `LearningConferenceDraft` und Status `draft`,
- SQLite-Schema oder Relationstabellen,
- ID-Format `LCD-######`,
- Create-/Update-/Load-/List-Verhalten,
- Domainvalidierung fuer Zeitraum, Datum und Referenzen,
- atomare Speicherung des Draft-Aggregats,
- kanonische Kompetenzstatus-Projektion,
- aktive Auswahl versus historische Draftreferenzen,
- Erhalt nicht verfuegbarer Beobachtungsreferenzen,
- Schnellbeobachtung als reinen Textbeleg,
- manuelle Autorenschaft aller paedagogischen Texte,
- vorhandene sechs Phasen und ihre fachlichen Felder,
- fehlenden LEG-Abschluss, fehlende Revisionen, fehlenden Snapshot,
- fehlendes LEG-PDF sowie fehlende Druck-/Exportartefakte.

`docs/REPORT_LEG_PRODUCT_MODEL_PROPOSAL.md` ist ein nicht bindender Discovery-Vorschlag. Seine Konzepte `completed`, Abschluss, Revision, Snapshot, Korrektur und Export duerfen nicht in UI-Sprint 6B vorweggenommen werden.

## 19. Konkreter Scope fuer UI-Sprint 6B

### Umsetzen

1. Bestehenden `LearningConferenceDialog` auf stabilen Kopf, linke Phasenleiste, einen aktiven Phasenworkspace und persistente untere Aktionsleiste umbauen.
2. Die sechs bestehenden Titel und alle bestehenden Draftfelder erhalten.
3. Vorbereitungs-, Gespraechs- und Vereinbarungsrollen gemaess Abschnitt 6 sichtbar trennen.
4. `agreed_goals_text` sichtbar dem Anker `goals` zuordnen; Persistenz unveraendert lassen.
5. Kompetenz-/Belegauswahl im Anker `evidence` konzentrieren; read-only Zusammenfassung in anderen Ankern.
6. Bestehende Design-System-Komponenten und zentrale Motion-Policy verwenden.
7. Kursname aus der bereits vorhandenen Schuelerprojektion in den reinen LEG-Vorbereitungskontext aufnehmen; keine neue Datenquelle und kein Schemafeld.
8. Dirty-State, lokal lesbaren Speicherzeitpunkt, Inline-Validierung und sicheren Dirty-Close-Dialog einfuehren; kein Autosave.
9. Optionalen Ueberpruefungstermin mit echtem leeren Zustand darstellen.
10. Mehrfach-Draft-Auswahl ruhig und ohne dominierende technische ID gestalten.
11. Profilmenue-Text auf `Lernentwicklungsgespraech oeffnen` praezisieren; Route und `student_id`-Navigation beibehalten.
12. 1400 x 900, 1280 x 800 und 1180 x 760 sowie Tastatur-/Accessible-Name-Verhalten gezielt testen.
13. Governance-Dokumente in der vorgeschriebenen Reihenfolge fuer neue sichtbare Felder/technische Namen aktualisieren, bevor produktiver Code geaendert wird.

### Nicht umsetzen

- Schema- oder Domainaenderung,
- neue Gespraechsphase oder gespeicherter Phasenstatus,
- Abschluss-, Finalisierungs-, Freigabe-, Revisions- oder Snapshotlogik,
- LEG-Vorschau als offizielles Dokument,
- LEG-PDF, Druck, Export oder Artefaktablage,
- automatische Textvorschlaege, KI oder paedagogische Interpretation,
- Berichtskomponenten fuer Revision, Finalisierung oder PDF,
- universelles Dokument- oder Workflowmodell,
- neue Zuordnung von Beobachtungen zu Querschnittsthemen.

### Erforderliche Tests in UI-Sprint 6B

- alle bestehenden Persistenz- und Referenztests unveraendert gruen,
- Phasenwechsel veraendert den Draftinhalt nicht,
- alle Felder werden aus bestehendem Draft in der richtigen Phase rekonstruiert,
- Rollenlabels und Accessible Names sind korrekt,
- `agreed_goals_text` bleibt round-trip-stabil,
- Auswahl bleibt bei Suche, Filter und Phasenwechsel erhalten,
- historische und nicht verfuegbare Referenzen bleiben sichtbar,
- Dirty-State nach Aenderung und Reset nach erfolgreichem Speichern,
- Dirty-Close mit allen drei Entscheidungen,
- kein LEG-Export-/Abschlussbutton vorhanden,
- Groessenpruefungen fuer 1400 x 900, 1280 x 800 und 1180 x 760 ohne horizontales Gesamtscrollen,
- Tastaturnavigation der Phasen und Fokusreihenfolge.

## 20. Risiken und offene Punkte

### Risiken

- Eine reine Layoutportierung ohne Rollenlabels wuerde die bestehende Verwechslung nur in einzelne Phasen verschieben.
- Ein Stepper mit Haken oder Prozenten wuerde fachliche Vollstaendigkeit behaupten, die der Draft nicht kennt.
- Persistieren der zuletzt aktiven Phase wuerde eine Schema- oder neue lokale Datenquellenentscheidung erfordern und liegt ausserhalb von UI-Sprint 6B.
- Das Hinzufuegen von Kurskontext darf nur die bestehende Schuelerprojektion erweitern; keine redundante Draftspeicherung.
- Die heutige automatische Vorbelegung des Ueberpruefungstermins kann in vorhandenen Drafts bereits unbeabsichtigte Datumswerte erzeugt haben. UI-Sprint 6B darf diese Daten nicht still entfernen.
- Querschnittsthemen duerfen ohne fachliche Zuordnungsquelle keine automatisch passenden Belege suggerieren.
- Ein lokaler Dirty-State darf niemals mit dem persistenten Domainstatus `draft` verwechselt werden.

### Offene Product-Owner-Frage

1. Sollen `child_retrospective_text` und `development_fields_text` verbindlich als im Gespraech bearbeitete Inhalte gelten, waehrend `strengths_text` und `teacher_perspective_text` interne Lehrkraftvorbereitung bleiben? Der aktuelle Code speichert die Felder getrennt, bezeichnet im linken Leitfaden aber alle vier als Vorbereitung der Lehrkraft. Die Empfehlung dieses Zielbilds lautet: Kindrueckblick und Entwicklungsfelder im Gespraech bearbeiten; Staerken und Lehrkraftsicht intern vorbereiten.

Alle anderen Entscheidungen fuer UI-Sprint 6B sind aus bestehender Fachlogik, Code, Design-System und den hier getroffenen UX-Festlegungen ableitbar.
