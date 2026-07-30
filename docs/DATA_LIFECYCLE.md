# Data Lifecycle

## V3-only Datenbankinitialisierung

**Status:** V3-only-Schema-, Startup-, Compatibility-, Backup-/Restore-,
synthetischer Testdaten-Cleanup und Assignment-API lokal implementiert. Der
SJ-2E-Lifecycle der produktiven Membership-Reader und der
SJ-2F-Lifecycle der produktiven Writer sind lokal umgesetzt. Exakt
verifiziertes Final-V3 ist für die normale Runtime lokal freigegeben; die
manuelle macOS-Abnahme bleibt offen.

1. Der Startup-Resolver prüft Pfad, WAL-/SHM-Sidecars, Restorezustand,
   `user_version` und vollständigen Schemafingerprint read-only.
2. Exaktes Final-V3 wird erkannt und als `V3_SCHEMA_READY` ausschließlich für
   die normale Runtime zugelassen.
3. Fehlt die Datei in einem autorisierten First Run, fordert der Coordinator
   eine direkte Final-V3-Erzeugung an. Die Schemaquelle erstellt kein
   Zwischen-V2, migriert keine Daten und schreibt keinen Übergangsbeleg.
4. Nach der Erzeugung wird die Datenbank neu geöffnet und vollständig
   verifiziert. Erst der anschließende Zustand `V3_SCHEMA_READY` lässt die
   Runtime zu. Die Composition Root öffnet sie danach mit `create=False`.
5. Fehlt die Datei außerhalb des autorisierten First Runs oder ist ein
   vorhandenes Schema leer, unbekannt, beschädigt, unsicher oder in einem
   unvollständigen Restorezustand, wird fail-closed gestoppt.

Es gibt keinen V2-Startupzustand, keine V2-Bootstrapmeldung, keine automatische
oder manuelle V2-Datenübernahme und keine Installation synthetischer
V2-Initialdaten als Produktpfad. Die autorisierte direkte Neuanlage erzeugt
kein Schuljahr. Fehlt ein eindeutiges `current`-Schuljahr, bleibt dies nach
technischem Runtime-Start ein fachlicher Sperrzustand.

## Direkte Final-V3-Schemaerzeugung

Die Schemaquelle akzeptiert ausschließlich ein ausdrücklich bestimmtes neues
Ziel. Sie erzeugt das vollständige Schema atomar, setzt die finale
`user_version`, prüft kanonischen Fingerprint, `integrity_check` und
`foreign_key_check` und liefert erst dann Erfolg. Ein Fehler hinterlässt
keine als kompatibel geltende Teilstruktur.

`students` wird direkt ohne `group_id` und `course_id` angelegt.
`courses.year_level` ist verpflichtend.
`school_year_transitions.from_school_year_id` ist verpflichtend; eine
Initialanlage ist kein Schuljahreswechsel und erzeugt keine Transition.

## Synthetischer V3-Testdatenlauf

Der Testdatenbuilder arbeitet nur auf einem expliziten temporären,
nicht vorhandenen Datenbankpfad:

1. vollständiges Final-V3 direkt erzeugen;
2. deterministisches current-Schuljahr `2025/26` mit
   `2025-08-01` bis `2026-07-31` anlegen;
3. deterministische Stammgruppen und Kurse der Stufen 1, 2 und 3 anlegen;
4. synthetische Schülerstammdaten ohne Membershipfelder anlegen;
5. für jeden eingeschriebenen Testschüler ein vollständiges
   `enrolled`-Assignment anlegen;
6. notwendige synthetische Beobachtungs-, Bestätigungs-, Bericht- und
   LEG-Regressionsdaten ergänzen;
7. Constraints, Zuordnungsabdeckung und Determinismus prüfen.

Der Lauf öffnet, löscht, ersetzt oder migriert keine vorhandene Datenbank. Er
verwendet keine echten Namen, keine lokalen Nutzerdaten und keine vorhandenen
Backups.

## Backup und Restore des finalen Schemas

Backupformat und Datenbankschema bleiben getrennte Verträge. Der bestehende
Backupcontainer, Snapshot-, Integritäts-, Atomizitäts- und
Manipulationsschutz bleiben erhalten. Als produktive Datenbank akzeptieren
Backup und Restore ausschließlich die exakte Final-V3-Schemaidentität.
V2-, unversionierte oder unbekannte Datenbankschemata werden weder migriert
noch als Produktrestore übernommen.

Ein echter späterer Schuljahreswechsel verlangt vor seinem ersten Write ein
verifiziertes Sicherheitsbackup des exakten Ausgangsbestands. Dieser
Jahreswechsel-Backupnachweis ist keine V2-Cutover-Evidence.

## Assignment- und Schuljahreslifecycle

Ein Assignment liegt vollständig innerhalb eines Schuljahres. Aktuelle und
historische Reads erhalten ihr fachliches Datum ausdrücklich vom Aufrufer.
Kein Repository setzt automatisch das Systemdatum ein oder wählt bei mehreren
Treffern still einen Datensatz.

Zusammengesetzte produktive Reads verwenden pro Request genau eine
`SchoolYearAssignmentReadSession` auf der Connection und im konsistenten
SQLite-Read-Snapshot des Aufrufers. Batchauflösung erfolgt set-basiert; Gruppe,
Kurs und Kursverbund werden ohne Einzelquery je Kind gefiltert. Der
Kursverbundscope ist die Schnittmenge aus seinen Stammgruppen und Kursen.
Mehrere passende Intervalle ergeben immer `AMBIGUOUS`; kein Treffer ergibt
`NO_ASSIGNMENT`. `CURRENT_SCHOOL_YEAR_MISSING` wird nur durch aktuelle
Schuljahresabfragen erzeugt. `last_known_membership` ist ein eigener
historischer Read und niemals Fallback einer anderen Methode.

Die produktiv verdrahteten V3-Lifecycles besitzen jeweils eine äußere
`BEGIN IMMEDIATE`-Transaktion. Repositories mit übergebener Connection
beginnen, committen, rollen zurück und schließen nicht selbst:

1. `CreateStudentWithInitialEnrollment` schreibt Stammdaten und initiales
   `enrolled`-Assignment gemeinsam oder gar nicht.
2. `UpdateStudentMasterData` ändert ausschließlich Name und Notiz; Assignments
   bleiben unangetastet.
3. `EnrollStudent` verlangt Schuljahr, Zeitraum, Gruppe und Kurs explizit und
   blockiert Überschneidungen.
4. `ChangeStudentMembership` kürzt das bisherige Intervall am Tag vor dem
   Stichtag und legt das Folgeintervall ab dem Stichtag an. Ohne ausdrückliche
   Stammgruppenänderung bleibt die Stammgruppe erhalten; derselbe Zielzustand
   liefert `NO_CHANGE`.
5. `ExitStudentFromSchoolYear` erzeugt ein `exited`-Intervall ohne Gruppe und
   Kurs und archiviert das Kind nicht.
6. `ArchiveStudent` ändert kein Assignment, erzeugt kein `exited` und
   blockiert bei aktiver Einschreibung am expliziten `as_of`-Tag. Dieser Tag
   muss dem Kalendertag des gespeicherten technischen Archivzeitpunkts
   entsprechen.

Frühere fachliche Records behalten ihren historischen Kontext. Ein später
archiviertes Kind bleibt an historischen Treffertagen auflösbar. Produktive
Membership-Reader verwenden den beschriebenen Assignment-Read-Lifecycle;
produktive Einzelkind-Writer verwenden seit SJ-2F die getrennten
V3-Lifecycles. Sammel-/Mehrkindwechsel und Schuljahreswechsel bleiben
gesonderte spätere Vorgänge.

Ein echter Schuljahreswechsel prüft Vorschau und Quellen, erstellt ein
verifiziertes Backup, aktiviert Maintenance, verlangt Step-up und Bestätigung
und führt Schließen des Ausgangsjahres, Aktivieren des Zieljahres,
Assignmenterzeugung und Transition-Beleg in einer atomaren Transaktion aus.
`from_school_year_id` und `to_school_year_id` referenzieren vorhandene
Schuljahre. Rollback, Idempotenz und Historie bleiben verbindlich. Dieser
Lifecycle ist noch nicht implementiert.

## SJ-2F-Lifecycle für produktive Writer

1. `StudentDesktopAdapter.save_new_student` löst das eindeutige aktuelle
   Schuljahr über `SchoolYearRepository` auf und übergibt V3-Stammdaten,
   Stammgruppe, Kurs und den expliziten Gültigkeitszeitraum gemeinsam an
   `CreateStudentWithInitialEnrollment`. Fehlt oder passt das aktuelle
   Schuljahr nicht, beginnt kein Write. Scheitert das Assignment, wird auch
   der Schülerdatensatz zurückgerollt.
2. `StudentDesktopAdapter.save_existing_student` ruft ausschließlich
   `UpdateStudentMasterData` auf. Kurs, Stammgruppe, Schuljahr,
   Assignmentintervall und Status sind keine Parameter dieses Pfads.
3. `StudentMembershipChangeDialog` zeigt aktuelle Zuordnung, expliziten
   Stichtag, Zielkurs, optionale neue Stammgruppe und Vorschau. Erst die
   bewusste Bestätigung ruft `ChangeStudentMembership` für genau ein Kind auf.
   `NO_CHANGE` verändert keinen Datensatz.
4. `StudentExitDialog` ruft getrennt `ExitStudentFromSchoolYear` auf.
   Archivierung verwendet getrennt `ArchiveStudent`; beide Vorgänge werden
   nicht automatisch kombiniert.
5. Kursanlage und -bearbeitung verlangen eine bewusst gewählte
   `year_level` 1, 2 oder 3. Kurs- und Stammgruppendeaktivierung benötigen
   einen expliziten Stichtag und werden bei aktuellen oder zukünftigen
   `enrolled`-Assignments vor dem Stammdatenwrite blockiert. Historische
   Assignments bleiben unverändert.

Keiner dieser Abläufe besitzt die Runtime-Disposition. Die gesonderte
Startup-Aktivierung ändert diese Writer nicht. Der
Schuljahreswechsel-Assistent und der Mehrkindwechsel sind keine Variante
dieses Einzelkind-Lifecycles und bleiben offen.

## SJ-3A-Lifecycle der rein lesenden Schuljahreswechsel-Vorschau

SJ-3A liest genau einen konsistenten SQLite-Snapshot und schreibt weder
Schuljahr, Assignment, Plan noch Transition-Beleg:

1. Alle `school_years`, alle V3-Schüler, aktive und inaktive Gruppen und Kurse
   sowie deren kanonische `courses.year_level` werden vollständig gelesen.
2. Genau ein `current`-Schuljahr wird verlangt. Für jedes V3-Kind werden alle
   Assignment-Kandidaten am inklusiven Ende dieses Schuljahres gelesen.
3. Die geplanten Zieljahresdaten werden gegen alle vorhandenen Schuljahre
   sowie auf strikte Nachfolge und lückenlosen Beginn geprüft.
4. Der reine Projektor erzeugt stabil nach `student_id` sortiert genau ein
   Item je V3-Kind. Archivierte, ausgeschiedene, fehlende, mehrdeutige und
   ungültig referenzierte Fälle bleiben sichtbar und ungelöst.
5. Eine aktive gültige Stufe 1 beziehungsweise 2 erhält nur dann einen
   Kursvorschlag, wenn genau ein aktiver Kurs der Stufe 2 beziehungsweise 3
   existiert. Die Stammgruppe bleibt nur bei gültiger aktiver Referenz
   unverändert vorgeschlagen. Stufe 3 bleibt bis zu einer späteren bewussten
   Auswahl ungelöst.
6. Die Connection läuft mit `PRAGMA query_only = ON`; die Komposition prüft,
   dass sich `total_changes` nicht erhöht, und beendet den Read-Snapshot per
   Rollback.

`executable` ist eine reine Validierungsprojektion und keine
Ausführungsfreigabe. SJ-3A enthält kein Backup, Maintenance-Gate,
Authentifizierung, Aktivierung, Assignmentwrite und keinen Mehrkindwechsel.
Die editierbare UI-Vorschau bleibt SJ-3B; die spätere Ausführung benötigt
weiterhin den vollständigen getrennten Schutzlifecycle.

## SJ-2E-Lifecycle für produktive Assignment-Reader

Der implementierte SJ-2E-Readerablauf ist rein lesend und besitzt weder die
Final-V3-Runtime-Disposition noch einen Writer:

1. Der aufrufende Bildschirm- oder Application-Request bestimmt seinen
   aktuellen `as_of`-Kalendertag genau einmal. Ein Dashboard verwendet dabei
   denselben injizierten Zeitpunkt für Stundenplan und aktuelle
   Mitgliedschaften. Systemdatum innerhalb von Repository, Adapter, ViewModel
   oder Widget ist unzulässig.
2. Der Aufrufer öffnet genau einen SQLite-Read-Snapshot beziehungsweise eine
   Read-Transaktion und erzeugt darauf genau eine
   `SchoolYearAssignmentReadSession`. Die Session übernimmt weder Beginn,
   Commit, Rollback, Close noch eine zweite Connection.
3. Die Session löst das eindeutige `current`-Schuljahr, die aktuellen
   `ENROLLED`-Mitglieder,
   `CURRENT_SCHOOL_YEAR_MISSING`-/`AMBIGUOUS`-Diagnostik und alle für
   den Request erforderlichen Gruppen-, Kurs- und Kursverbundzähler gemeinsam
   als `CurrentMembershipReadSnapshot` auf. Kursverbünde werden als
   Schnittmenge ihrer registrierten Gruppen und Kurse mit den aktuellen
   Assignments ausgewertet.
4. Schülerliste, Stammgruppen-/Kurs-/Kursverbundfilter, Dashboard-Heatmap,
   passende Kinder, Onboardingstatus und weitere aktuelle Leser konsumieren
   ausschließlich diesen Snapshot. Dokumentations-, Beobachtungs- und
   Stammdatenprojektionen des Requests werden auf derselben Connection und im
   selben Snapshot gelesen. Weder Python-Nachzählung noch Abfrage je Kind oder
   Unterwidget ist zulässig.
5. `EXITED`, `NO_ASSIGNMENT` und archivierte Schüler werden aus aktuellen
   Listen und Zählern ausgeschlossen. Ein Einzelprofil darf diese Zustände
   neutral anzeigen. Fehlendes `current`-Schuljahr oder `AMBIGUOUS` blockiert
   die aktuelle fachliche View; beides wird weder zu einer leeren Liste noch
   zu Nullzählungen normalisiert. Technische IDs sind keine sichtbaren
   Ersatzbezeichnungen.
6. Historische Quellen werden set-basiert als
   `AssignmentReferenceRequest(request_key, student_id, reference_date)`
   übergeben. Für Berichte ist ausschließlich `period_end`, für LEG
   ausschließlich `conference_date` und für Beobachtungen ausschließlich
   `observations.date` das Referenzdatum. Der Ergebnisbezug erfolgt über den
   unveränderten `request_key`.
7. Ein freies Dokument ohne fachliches Referenzdatum bleibt bezüglich
   Stammgruppe und Kurs neutral und erzeugt keinen
   `AssignmentReferenceRequest`. Ein fehlendes oder ungültiges Referenzdatum
   wird nicht durch current, `last_known_membership`, Systemdatum,
   Erstellungszeitpunkt oder V2-Schülerfelder ersetzt.
8. Nach vollständiger Projektion beendet der Aufrufer seinen Read-Snapshot.
   Der Ablauf schreibt keine Daten, erzeugt keine Migration und verändert
   weder finalisierte Revisionen noch PDFs.

Dieser Vertrag ist mit SJ-2E lokal umgesetzt. Die gesonderte
`V3_SCHEMA_READY`-Disposition lässt das exakt verifizierte Schema starten,
ohne diesen Readervertrag oder fachliche Sperrzustände zu verändern.

## Phase 2 Berichte-Übersicht - rein lesender Projektionsablauf

**Status:** lokal implementiert. Der Ablauf schreibt nichts und ergänzt weder
Persistenz noch Migration oder Recovery.

1. Die Projektion setzt genau einen bewusst gewählten RPD voraus und verwendet
   dessen `period_start` und `period_end` inklusiv. Ohne eindeutigen RPD
   entsteht keine inhaltliche Phase-2-Projektion. Schuljahr, Halbjahr,
   Kalenderjahr, Tagesdatum, LEG-Zeitraum und andere RPD sind keine Fallbacks.
   Auch ein einzelner vorhandener RPD wird nicht automatisch gewählt; eine
   fehlende oder veraltete bewusste Auswahl bleibt neutral.
2. Der Desktop-Adapter friert `period_start` und `period_end` des ausgewählten
   RPD einmal ein. Er liest aktive Beobachtungen, Zuordnungen sowie den
   kanonischen Kompetenzstatus über
   `SQLiteStudentDocumentationProjectionRepository.read_batch` in einem
   SQLite-Read-Snapshot. Bericht- und LEG-Aggregate liest er über getrennte
   schülerbezogene Revisionshistorien-Batches und verifiziert danach je
   Aggregat die neueste gültige Revision im vorhandenen Domain-Service.
   Quellenfehler werden neutral isoliert; ein defekter Zweig leert keine
   weiterhin gültige Teilprojektion. Bericht und LEG werden erst in der
   flüchtigen Displayprojektion zusammengeführt.
3. Ereignisdaten stammen ausschließlich aus ihren vorhandenen Fachwerten:
   `observations.date`, `confirmed_at` des aktuellen sicheren
   Bestätigungsstands, `finalized_at` der neuesten gültigen,
   hashverifizierten Revision eines abgeschlossenen Berichtaggregats sowie
   `conference_date` eines tatsächlich durchgeführten und fachlich
   abgeschlossenen LEG-Aggregats. `completed_at` bleibt ausschließlich
   technischer Lifecyclezeitpunkt. Zeitzonenbehaftete Werte werden lokal
   normalisiert; naive historische Werte behalten ihren gespeicherten lokalen
   Kalenderwert.
4. Ungültige oder fehlende Datumswerte erhalten keinen Ersatzwert. Der
   betroffene Inhalt bleibt aus Timeline und Zeitraumzählern ausgeschlossen;
   die Displayprojektion liefert zusätzlich einen neutralen unvollständigen
   Zustand.
5. `Beobachtung dokumentiert` entsteht global höchstens einmal je
   `observation_id`. Vorhandene Zuordnungen
   `(observation_id, competency_id)` liefern neutrale
   Beobachtungskartendetails, Fachkartenmengen, Segmente, Belegdetails,
   Fachzuordnung und Deduplizierung, aber keine eigenen Timeline-Ereignisse.
   Eine Schnellbeobachtung ohne Zuordnung bleibt eine Beobachtung.
   `Kompetenz bestätigt` entsteht höchstens einmal je Paar
   `(student_id, competency_id)` aus dem aktuellen sicheren Stand.
6. Die verpflichtende Dokumentereignismenge enthält innerhalb des eindeutig
   gewählten RPD-Zeitraums je fachlich abgeschlossenem Berichtaggregat
   höchstens ein Ereignis mit Identität `("report", report_draft_id)` und je
   tatsächlich durchgeführtem und fachlich abgeschlossenem LEG-Aggregat
   höchstens ein Ereignis mit Identität
   `("learning_conference", learning_conference_draft_id)`. Die jeweils
   neueste gültige, hashverifizierte Revision liefert ausschließlich sichtbaren
   Stand und Navigationsziel; frühere Revisionen bleiben in ihrer getrennten
   Revisionshistorie. `Draft geöffnet`,
   `Draft gespeichert`, `updated_at`, technische Bearbeitungs- oder
   Verwaltungszeitpunkte und bloße Zwischenstände ohne fachlichen Abschluss
   erzeugen kein Phase-2-Timeline-Ereignis. Dokumentereignisse werden nicht
   wegen einer Ziel- oder Viewportgröße entfernt; liegen mehr als 15 gültige
   Bericht-/LEG-Abschlussereignisse vor, bleiben alle enthalten.
7. Die Timeline besitzt einen Zielumfang von 15 Ereignissen. Enthält die
   verpflichtende Dokumentereignismenge weniger als 15 Ereignisse, ergänzt die
   ViewModel-Projektion genau so viele der zeitlich neuesten zulässigen
   Beobachtungs- und Bestätigungsereignisse, wie zum Erreichen von 15 noch
   fehlen. Zulässig sind ausschließlich aktive Beobachtungen und der aktuell
   vorhandene sichere Bestätigungsstand mit fachlichem Datum im
   RPD-Zeitraum. Reichen die
   zulässigen ergänzenden Ereignisse nicht aus, bleibt die Timeline kürzer; es
   entstehen keine künstlichen Ereignisse. Bei mindestens 15 verpflichtenden
   Dokumentereignissen wird nichts zu deren Begrenzung entfernt.

   Für die Auswahl ergänzender Ereignisse gilt: fachlich neuerer Zeitpunkt
   zuerst; bei identischem fachlichem Zeitpunkt entscheidet ausschließlich die
   stabile technische Quellidentität in aufsteigender lexikografischer
   Reihenfolge. Nach Abschluss der Inhaltsauswahl wird die gesamte ausgewählte
   Ereignismenge chronologisch vom ältesten zum neuesten Ereignis sortiert.
   Auch in dieser Anzeigeordnung entscheidet bei identischem fachlichem
   Zeitpunkt die stabile technische Quellidentität aufsteigend und
   lexikografisch. Zusammengesetzte Identitäten werden in ihrer bereits
   dokumentierten Komponentenreihenfolge komponentenweise verglichen. Auswahl
   und Anzeigeordnung sind deterministisch und unabhängig von Rating, Fach,
   Ereignistyp außerhalb der verpflichtenden Bericht-/LEG-Aufnahmeregel,
   Wichtigkeit, Stärke, Defizit, Förderbedarf, pädagogischer Relevanz oder
   automatischer Priorität.
8. Je Fach werden zwei unabhängige Identitätsmengen gebildet: aktuelle
   dokumentierte `competency_id` und vorhandene `observation_id` im
   RPD-Zeitraum. Eine aktive, aktuelle Kompetenz gehört zur ersten Menge,
   wenn mindestens eine aktive Beobachtungszuordnung im RPD-Zeitraum
   vorhanden ist. Mehrfachbeobachtungen derselben Kompetenz erhöhen den
   Kompetenzzähler nicht mehrfach. Eine Bestätigung derselben Kompetenz
   erzeugt weder ein zusätzliches Segment noch ohne Beobachtungszuordnung eine
   dokumentierte Kompetenz.

   Für die Fachmenge einer aktiven Beobachtung gilt:

   - Existiert mindestens eine vorhandene Zuordnung
     `(observation_id, competency_id)`, entsteht die Fachmenge aus allen
     vorhandenen fachlichen `subject_id` der zugeordneten Kompetenzen
     beziehungsweise Ratings. Jede `subject_id` kommt in dieser Menge
     höchstens einmal vor; dieselbe `observation_id` zählt innerhalb derselben
     Fachkarte höchstens einmal. Die Beobachtung darf in mehreren tatsächlich
     betroffenen Fachkarten erscheinen, bleibt global aber dieselbe, allein
     über `observation_id` identifizierte Beobachtung.
     `observations.subject_id` ist in diesem Fall kein Fallback.
   - Existiert keine Kompetenzzuordnung, wird ausschließlich die stabile
     `observations.subject_id` verwendet. Daraus wird keine Kompetenz
     abgeleitet; die Beobachtung zählt nur als Beobachtung. Fehlende
     Fachzuordnungen werden weder geraten noch aus Anzeigenamen, Textinhalten
     oder UI-Beschriftungen erzeugt.
   - `cross_subject` ist keine eigenständige Fachkarte. Es erzeugt weder eine
     zusätzliche Fachkarte noch einen künstlichen Fachzähler und ersetzt keine
     fehlende konkrete Fachzuordnung. Fachkarten werden ausschließlich
     tatsächlich vorhandenen fachlichen `subject_id` zugeordnet.

   Historische Kompetenzen zählen nicht zum aktuellen Kompetenzbestand, machen
   ihre realen Beobachtungen aber nicht unsichtbar.
9. Eine Bestätigung zählt nur aus dem aktuellen kanonisch sicheren Stand
   einer aktiven, nicht historischen Kompetenz mit gültigem `confirmed_at` im
   RPD-Zeitraum. `confirmation_unknown` zählt nicht.
   `newer_observations` rekonstruiert keine Bestätigungskette und hebt den
   vorhandenen aktuellen Stand nicht auf.
10. Nach Navigation oder Refresh wird die gesamte flüchtige Projektion aus den
    vorhandenen Quellen neu gebildet. Es gibt keinen Phase-2-Cache,
    Timeline-Writer oder neuen Schreibprozess.

## Berichte-Übersicht 0.3.1 / Paket 1 lesen und navigieren

Der folgende Ablauf ist die historische Paket-1-Basis. Seine
platzbegrenzte Meilensteinanzeige und die Profil-Orientierungsquelle sind im
Berichtsbereich durch den vorstehenden Phase-2-Ablauf ersetzt.

1. Das Schülerprofil fragt die Paket-1-Übersicht über
   `StudentDesktopAdapter.report_overview_for_student(student_id)` an.
2. Der Adapter liest RPD und RPT/RPV über die vorhandenen Bericht-Application-
   Services sowie LCD und LCF/LCV separat über die vorhandenen LEG-Application-
   Services.
3. Bei genau einem RPD wird dessen Start- und Enddatum als einzige
   Berichtszeitgrundlage projiziert. Bei mehreren RPD bleibt die Übersicht
   leer, bis die Lehrkraft einen Entwurf ausdrücklich wählt; diese Auswahl wird
   nur für die laufende Shell-Sitzung behalten und kann bewusst gewechselt
   werden. Ohne Auswahl entsteht keine inhaltlich gemischte Übersicht.
4. Drafts und Revisionen werden erst im ViewModel als gemeinsame read-only
   Anzeigeliste nach letzter relevanter Aktivität sortiert. Ihre fachlichen
   Aggregate und Repositories bleiben getrennt.
5. Die kompakte Meilensteinanzeige verwendet aus dieser Anzeigeliste nur die
   neuesten, in den verfügbaren Platz passenden Bericht-/LEG-Ereignisse und
   ergänzt reale datierte Kompetenzbestätigungen aus der bereits vorhandenen
   Profilprojektion. Sie begrenzt ausschließlich die Sichtbarkeit, berechnet
   keine Entwicklung und deutet eine Bestätigung nicht als Kompetenzabschluss.
6. Eine Kartenaktion übergibt ausschließlich technische Student-, Draft-,
   Revisions- oder Fach-IDs an die Shell. Bei Mehrdeutigkeit öffnet sie die
   bestehende Auswahl; es gibt keine automatische Entwurfsaktivierung.
7. Jeder neue RPD öffnet unabhängig von bereits vorhandenen RPD zuerst eine
   nicht persistente Zeitraumauswahl; erst nach der bewussten gültigen Auswahl
   öffnet sich der einzige bestehende Berichteditor. Mit genau einem RPD öffnet
   er diesen direkt, bei mehreren RPD entweder nach der bewussten Wahl eines
   vorhandenen RPD oder nach zusätzlicher Zeitraumwahl für `Neuer Entwurf`.
   Danach aktiviert `Bericht vorbereiten` `Kompetenzen & Belege`, setzt den
   vorhandenen Fachfilter und sichtbaren Fokus. Es wird keine Kompetenz
   ausgewählt oder gespeichert.
8. Nach Schließen des Bericht- oder LEG-Arbeitsraums liest das Schülerprofil
   alle Paket-1-Projektionen erneut. Speichern, Zeitraumwechsel, Finalisierung
   und Abschluss bleiben dadurch konsistent sichtbar.

Dieser Prozess ist vollständig lesend, bis die Lehrkraft in einem bereits
dokumentierten bestehenden Arbeitsraum eine dortige Schreibaktion bewusst
auslöst. Paket 1 ergänzt keinen Schreibprozess, keine Tabelle, keine Migration,
keinen Cache und keinen Recoverypfad.

## Pilot-Releaseautomation

1. `inspect` bindet sauberen Branch, HEAD, Remote, zentrale Version,
   `gh`-Status, öffentlichen Pilot-Appcast, Tag-/Releasefreiheit und
   deaktivierten Stable-Kanal read-only.
2. `prepare` erzeugt atomar lokales und sanitisiertes Manifest. Version und
   Build müssen bereits im Manifest-Commit stehen und höher als der aktuelle
   Pilotbuild sein.
3. `build` checkt exakt den Manifest-Commit detached in einen privaten
   temporären Worktree aus. Ein frisches Venv installiert ausschließlich
   committed Pins; alte Build- und Dist-Wurzeln werden nicht übernommen.
4. DMG, Dokumentations-ZIP, Prüfsummen, Inventar und lokale Release Notes
   werden mit Größe und SHA-256 an das Manifest gebunden. Ein Buildfehler
   setzt nur die Phase `built` auf `failed`.
5. `package-test` mountet das DMG read-only und prüft Metadaten, arm64,
   Codesign, native Laufzeiten, Sparkle, App-Start, verbotene Artefakte,
   private Pfade, Pilotfeed und Stable-Sperre. Der Restore-Smoke ist getrennt.
6. `publish-github` pusht ohne Force, erzeugt einen annotierten Tag und zuerst
   ein Draft-Pre-Release. Alle exakt erlaubten Assets werden erneut
   heruntergeladen und gegen Manifestgröße und SHA-256 geprüft, bevor der
   Draft als nicht-Latest Pre-Release veröffentlicht wird.
7. `publish-appcast` lädt das veröffentlichte DMG erneut, verifiziert seine
   Identität und lässt es über den bestehenden Keychain-Account signieren.
   Nur neuer Pilot-Appcast und Release-Notes-Seite werden einzeln gestaged.
   Stable bleibt bytegleich beziehungsweise nicht vorhanden.
8. `verify` liest ausschließlich öffentliche GitHub-, Asset-, Release-Notes-
   und Feedzustände. Tagziel, Hashes, Version, Build, Architektur,
   Mindest-macOS und Ed25519-Signaturen müssen übereinstimmen, bevor
   `remote_verified` gesetzt wird.

Jede Phase benötigt vollständig bestätigte Vorgänger. Ein exakter vorhandener
Zustand darf idempotent fortgesetzt, ein abweichender Zustand niemals
überschrieben werden. Ein GitHub-Ausfall nach Build oder Appcast-Ausfall nach
GitHub-Veröffentlichung invalidiert keine zuvor bestätigte Phase. Private
Schlüssel, GitHub-Tokens, Passwörter und Produktdaten werden nicht in Manifest,
Logs, Argumentlisten oder Releaseausgabe übernommen.

## Performance-P1 - konsistenter Dokumentations-Refresh

Schuelerliste und Dashboard-Heatmap oeffnen fuer ihre gemeinsame fachliche
Basis genau einen kurzlebigen SQLite-Read-Snapshot. Darin werden aktive
Schueler im angeforderten Scope, aktive Gruppen und Kurse, der
Kompetenzkatalog, die Dokumentationsfachauswahl, aktive Beobachtungen,
Kompetenz-Snapshots, Bestaetigungen und Persistenzereignisse gebuendelt
gelesen. Erst nach Abschluss des Snapshots gruppiert der Desktop-Adapter die
Daten je Schueler und verwendet unveraendert die kanonische
Dokumentationsregel: Eine konkrete Kompetenz ist durch mindestens eine aktive
Beobachtung oder eine Bestaetigung dokumentiert; der Frischezustand
einschliesslich `confirmation_unknown` aendert diese Abdeckung nicht.

Der Batch wird nach dem Refresh verworfen. Er schreibt nichts, initialisiert
kein Schema, legt keinen globalen Cache an und veraendert weder Gate-Off-
Semantik noch Transaktions-, Backup-, Restore-, Bericht- oder LEG-Prozesse.

Verifiziertes Querybudget auf dem macOS-Offscreen-Messpfad vom 26.07.2026:

| Bestand | Projektion | Audit vorher | Batch danach | geladene Projektionszeilen |
|---|---|---:|---:|---:|
| 30 Schueler / 300 Beobachtungen | Schuelerliste / Heatmap | je rund 6.365 Statements und 0,34 s | je 9 `SELECT`, 11 Statements und 0,025 / 0,023 s | 1.121 |
| 300 Schueler / 9.000 Beobachtungen | Schuelerliste / Heatmap | rund 69.605 Statements und 3,51 / 3,53 s | je 9 `SELECT`, 11 Statements und 0,277 / 0,246 s | 18.791 |
| 1.000 Schueler / 120.000 Beobachtungen | Schuelerliste / Heatmap | Heatmap 322.004 Statements und 13,66 s | je 9 `SELECT`, 11 Statements und 1,745 / 1,803 s | 241.491 |

Die Batch-Nachmessung verwendet den produktiven aktiven Katalog mit 466
Einträgen. Die beiden größten Reads sind erwartungsgemäß aktive Beobachtungen und deren
Kompetenz-Snapshots; beim großen Bestand benötigten Laden plus Hydrierung
jeweils rund 0,46 bis 0,53 s. Das Querybudget ist unabhängig von Schüler- und
Beobachtungszahl. Der fokussierte gemeinsame Shell-Startpfad blieb bei allen
drei Beständen bei 71 `SELECT` und ohne DDL; 300 / 9.000 benötigte 0,915 s.

## P1-Paket 1 - Ereignismigration, Frische und Attachment-Recovery

### Historischer Frische-Backfill ist kein Produktpfad

Der frühere V1→V2-Backfill synthetischer Entwicklungsdaten ist durch ADR-096
obsolet. Das finale Schema enthält `persistence_events` direkt. Es gibt keinen
Produktrestore und keine Schemamigration, die historische V1-/V2-Daten
übernimmt. Die nachfolgende Ereignissemantik für neu erzeugte Final-V3-Daten
bleibt davon unberührt.

### Neue Frischeereignisse

Observation-Create schreibt einen allgemeinen `observation_created`-Anker und
je Rating ein `observation_competency_changed`. Ein Edit schreibt einen
`observation_updated`-Anker und nur bei Rating-Hinzufügung, -Entfernung,
-Wertänderung oder Schülerwechsel Frischeereignisse je altem/neuem Paar.
`date`, `subject_id`, Kontext, Notiz, Snapshot-Anzeigetexte und Anhänge ändern
die Bestätigungsfrische nicht. Soft Delete `active 1 -> 0` schreibt
`observation_deactivated` je Rating; Reaktivierung ist nicht freigegeben.
Confirmation-Upsert und `confirmation_upserted` liegen in derselben
Transaktion. Ein exakter No-op mutiert weder Fachzustand noch Ereignisse.

Die Live-Projektion vergleicht die jüngste relevante Observation- und
Confirmation-Sequenz. Ein historischer Grenzgleichstand projiziert
`confirmation_unknown` und sichtbar
`Bestätigungsstand unklar – bitte erneut bestätigen`. Ein neues geordnetes
Frischeereignis löst den Altzustand eindeutig auf. Evidence bleibt getrennt
und liest weiterhin nur aktive Beobachtungen.

### Beobachtung plus Anhänge

1. Dialog und Draft halten ein stabiles `operation_token`.
2. Unter demselben kernelgebundenen Writer-Lock werden vor neuen Operationen
   unvollständige Journale recovered; beschädigte oder widersprüchliche
   Journale bleiben als reservierende Evidenz erhalten und blockieren
   fail-closed.
3. OBS-/MED-IDs werden aus SQLite plus allen Journal- und Finaldatei-
   Reservierungen vergeben und vor Nutzung dauerhaft im Journal gebunden.
4. Jede Quelle wird genau einmal no-follow geöffnet, über denselben FD
   gehasht und in ein exklusives Stagingziel kopiert; `fstat` vor/nach sowie
   Staginggröße und -hash müssen übereinstimmen.
5. Publikation erfolgt im selben Datenroot per exklusivem Hardlink. Ein
   vorhandenes Ziel ist nur als exakt inode-, größen- und hashgleicher
   Crash-Retry zulässig.
6. Danach schreibt genau eine SQLite-Transaktion Observation, Ratings,
   Ereignisse und neue Dokumentreferenzen; Altanhänge werden erst zuletzt
   deaktiviert.
7. Rollback erhält den vorherigen SQLite-Zustand und aktive Altanhänge.
   Vorpublizierte neue Dateien bleiben journalgebunden und werden beim Retry
   wiederverwendet.
8. Nach Crash wird entweder der gebundene Vorherzustand fortgesetzt oder der
   exakte Sollzustand samt vollständigem Eventsatz als bereits committed
   erkannt. Jeder andere Zustand blockiert.
9. Backup und Restore-Staging erwerben denselben Writer-Lock und führen
   ausstehende Recovery vor Snapshot beziehungsweise Staging aus. Ein
   widersprüchliches Journal verhindert die Sicherung oder
   Restore-Vorbereitung.

Die Phasen sind `PREPARED`, `FILES_STAGED`, `FILES_PUBLISHED`,
`DATABASE_COMMITTED` und `COMPLETE`. `PREPARED` bindet Operation, IDs,
Sollzustand und Attachment-Intent bereits vor dem ersten Quellenzugriff;
`FILES_STAGED` ergänzt die verifizierte Byte-Evidenz. Journal und Staginglink
bleiben als Retrybeleg erhalten; beschädigte Zustände werden nicht umbenannt
oder automatisch bereinigt, sondern blockieren. Produktiver Restore-Austausch,
Restore-Staging, Backup und alle MED-Schreiber verwenden denselben
kernelgebundenen, pro Thread reentranten Writer-Lock. SQLite und Dateisystem
werden ausdrücklich nicht als gemeinsam atomar beschrieben.

## Security Sprint 12 - interner Build- und Pakettest-Lifecycle

1. Branch, Referenz-HEAD, Index, gemischten Worktree, geschützte Exceldatei,
   Versionsquellen, Requirements, Spec, native Laufzeiten und offene
   Plattformgrenzen read-only inventarisieren.
2. Den macOS-arm64-Build nur in einem explizit validierten Build- und
   Distributionsroot ausführen. Abhängigkeiten aus der gepinnten Builddatei in
   ein neues Venv installieren und Versionen, SQLCipher-Engine sowie
   arm64-Verfügbarkeit vor PyInstaller fail-closed prüfen.
3. Das App-Bundle mit Security-Testmodulen, SQLCipher, PyNaCl/libsodium,
   `_cffi_backend`, Security-/Sparkle-Bridges und Lizenztexten bauen. Nach dem
   Kopieren universelle Mach-O-Dateien auf arm64 reduzieren und erst danach
   das vollständige Bundle signieren.
4. Bundlemetadaten, native Architektur, benötigte Module, Lizenzen, verbotene
   Artefakte und textuelle Entwicklerpfade statisch prüfen. Ein Fehler beendet
   den Build vor DMG-Erzeugung.
5. Gate-Off mit dem normalen Paket-Smoke in einem separaten
   `JENAPLAN_APP_DATA_DIR` prüfen. Der Lauf muss normalen SQLite-, Dokument-,
   PDF-, ZIP-v1-Backup- und Beendenpfad verwenden und bestätigt ausdrücklich,
   dass kein Sprint-11-Orchestrator importiert wurde.
6. Gate-On ausschließlich mit Paketmarker, exaktem Gatewert und beiden
   Sprint-11-Markern prüfen. Separate Prozesse führen Migration, Reopen,
   verschlüsseltes Backup, Restore-Staging, falschen Key, Manipulation,
   deaktiviertes Gate bei vorhandenem Bestand sowie echte Abbrüche und
   Neustart-Recovery aus.
7. Den DMK-Keychain-Lifecycle in einem getrennten synthetischen Security-Root
   prüfen: anlegen, in einem neuen Prozess und kopierten Bundle lesen,
   Passwort ändern ohne DMK-Rotation, fehlenden/falschen Eintrag blockieren,
   widerrufen und löschen. Zugriffverweigerung und Developer-ID-/Notarisierungs-
   wechsel bleiben reale manuelle Gates.
8. Erst nach Tests, Bundle-/Secret-/Pfad-/Klartextscan und vollständiger
   Dokumentation darf ein interner RC als technisch vorbereitet gelten. Ein
   uncommitteter oder inhaltlich nicht reproduzierbarer Stand bleibt NO-GO.

Die Pakettestbefehle sind keine Startup-, UI-, Produktmigrations- oder
Recoveryfunktion. Sie dürfen weder normale App-Daten noch Pilotbestände
adressieren und erzeugen keine produktive Schlüsselablage.

## Releasebasis 0.3.0 / Build 303

Bestätigungsdialoge und Passwort-Eingabehinweise verarbeiten ausschließlich
flüchtigen Widgetzustand. Touch-ID-Verfügbarkeit liest weiterhin nur die
kanonische Statusprojektion; eine deaktivierte oder nicht verfügbare Option
verändert weder Credential, Keychain, Passwort, Recovery-Code noch
Security-Epoch. Ein Passwort wird nur über die bestehenden Authentifizierungs-
und Passwortwechsel-Services verarbeitet und weder protokolliert noch in
Zwischenablage, Preferences oder einer neuen Plattformbrücke abgelegt.

Der paketierte Restore-Neustart startet `sys.executable` als neue unabhängige
PyInstaller-Instanz. Nur dieses Kind erhält
`PYINSTALLER_RESET_ENVIRONMENT=1`; Standard-Ein- und -Ausgaben sind gültig an
`DEVNULL` gebunden. Der Runtime-Lock-FD bleibt der einzige zusätzlich
vererbte Deskriptor. Endet das Kind vor dem bestätigten Startup-Handshake,
wird sein Exitcode im bestehenden technischen Handshake-Zustand erfasst und
der vorhandene vollständige Rollback ausgeführt.

## Security Sprint 11 - kontrollierter Integrations-Lifecycle

### Startup und Gate

1. Ohne `JKM_SECURITY_INTEGRATION_TEST=1` wird kein Sprint-11-Pfad aufgelöst
   oder importseitig ausgeführt; der bestehende Startup bleibt unverändert.
2. Mit Gate werden Root, Eigentümer, Modus, Temporärgrenze, Marker,
   Klartextquellmarker, feste Rollen und Symlinkfreiheit read-only geprüft.
3. Produkt-, Pilot-, RC-, unmarkierte, gemischte oder bereits widersprüchliche
   Bestände wechseln nach `BLOCKED`; es gibt keinen Fallback.
4. Authentifizierung muss abgeschlossen sein. Erst danach liefert der
   injizierte DMK-Loader denselben aktiven DMK; Passwort und DMK bleiben
   getrennt.
5. App-Instanz- und Migrations-Lock werden vor Mutation exklusiv erworben.

### Migration und Recovery

1. `PREFLIGHT` bindet Installation, Datenbankkontext, Migration, DMK- und
   Database-Key-Generation, Root, Klartextdatenbank sowie jede
   Dokumentquelle mit sicherem relativem Namen, Größe und SHA-256 in Journal
   und Replay-Anker.
2. Die geschlossene, WAL-/SHM-ruhige Quelle wird byte-identisch nach
   `MigrationSafetyCopy` kopiert, Datei und Verzeichnis werden synchronisiert
   und beide Bestände read-only auf Hash und SQLite-Integrität verglichen;
   danach folgt `BACKUP_VERIFIED`.
3. Eine separate SQLCipher-Datei wird über die zentrale Connection Factory
   mit gesetztem Key angelegt. Schema und Daten werden ohne `ATTACH` und
   `sqlcipher_export` übertragen, verglichen, geschlossen und neu geöffnet.
   Erst danach wird `SecurityIntegrationSchemaV1` transaktional ergänzt und
   `DATABASE_MIGRATED` bestätigt.
4. Für jedes registrierte Dokument wird ein zufälliger opaque Storage-ID-Plan
   vorab journalisiert. Der Container wird als Retained-Datei geschrieben,
   gefsynct, vollständig verifiziert und No-Clobber veröffentlicht. Der
   SQLCipher-Generationssatz bleibt `PREPARED`; danach folgt
   `DOCUMENTS_PREPARED`.
5. Eine einzige SQLCipher-Transaktion prüft alle vorbereiteten Generationen,
   setzt sie `ACTIVE`, markiert etwaige Vorgänger `RETAINED` und ersetzt die
   alten `documents.file_path`-Werte durch opaque Storage-Referenzen. Erst
   danach folgt `REFERENCES_SWITCHED`.
6. SQLCipher-Datenbank und alle aktiven verschlüsselten Dokumentcontainer
   werden in einen neuen verschlüsselten Backupcontainer geschrieben und
   vollständig verifiziert; danach folgt `ENCRYPTED_BACKUP_VERIFIED`.
7. Alle Handles werden geschlossen. Ein neuer Factory-Open validiert Key,
   SQLCipher/SQLite-Integrität, PRAGMAs, Integrationsschema, aktive Pointer und
   jeden Container; danach folgt `REOPEN_VERIFIED`.
8. Erst jetzt wird die unveränderte Klartextquelle samt Safety Copy als
   Retained markiert. `COMPLETED` folgt ausschließlich nach erneuter
   Gesamtprüfung. Es erfolgt keine physische Löschung.

Vor jeder Phasenpublikation bereitet der externe Replay-Anker die nächste
Journalrevision vor. Nach atomarer Journalpublikation wird der Anker
committed. Ein Neustart löst nur exakt passende pending Zustände auf. Jede
Phase ist wiederholbar: vorhandene Artefakte werden neu verifiziert statt
überschrieben. Unbekannte, ausgetauschte oder nicht phasengerechte Bestände,
Anchor-Rückschritt und Crossbinding-Abweichung führen zu `BLOCKED` oder
`RECOVERY_REQUIRED`.

### Dokumentaktionen

- Import publiziert erst einen vollständig verifizierten Container und
  aktiviert die Datenbankreferenz erst anschließend transaktional.
- Kontrolliertes Lesen liefert Klartext nur an einen injizierten Consumer und
  meldet Erfolg erst nach zweiter vollständiger Final-/EOF-/Hashprüfung.
- Bewusster Export erzeugt exklusiv eine neue unverschlüsselte Datei im
  markergebundenen Exportbereich außerhalb des verwalteten Storage und gibt
  den Schutzverlust als festen Hinweis zurück.
- Austausch erzeugt eine neue unveränderliche Dokumentgeneration. Die alte
  aktive Generation bleibt bis zur bestätigten Pointer-Umschaltung nutzbar
  und wird anschließend nur `RETAINED`.
- Soft-Löschen und GC bleiben konservativ; es gibt in Sprint 11 keine
  automatische physische Entfernung.

### Backup, Restore, Passwort und Support-Reset

- Das bestehende ZIP-v1-Backup/Restore bleibt außerhalb des Gates unverändert.
- Der Integrationsadapter akzeptiert nur das validierte Sprint-11-SQLCipher-
  Schema und verschlüsselte Dokumentcontainer. Writer und Restore
  überschreiben kein Ziel.
- Restore erfolgt in einen neuen Staging-Root. Datenbank-Key, Schema,
  Integrität, Dokumentcontainer, Hashes und Abschlussbeleg werden vollständig
  geprüft. Eine Produkt-Live-Umschaltung ist ausgeschlossen.
- Passwortwechsel und Support-Reset verändern weder DMK noch Database-,
  Document- oder Backup-Key. Fehlender oder beschädigter Plattform-DMK
  blockiert; stille Schlüsselerneuerung ist verboten.

## Security Sprint 10 - isolierter Dokumentcontainer-Lifecycle

### Neue Dokumentgeneration schreiben

1. Privaten markergebundenen Test-Root sowie seine festen, nicht symlinkenden
   `sources`-, `storage`- und `exports`-Unterbereiche prüfen. Produktpfade und
   unbekannte Roots blockieren.
2. Die synthetische Quelle unter `sources` no-follow und identitätsgebunden
   öffnen. Reguläre Datei, einfacher Link, feste Synthetiksignatur, erlaubter
   MIME-Typ, Größenlimit, unveränderte Identität und begrenzte Reads prüfen.
3. Opaque Storage-ID, Container-ID, zufälligen 256-Bit-Document-Key und
   Document-Key-ID erzeugen. Dokumentgeneration, Key-Generation und
   Envelope-Revision sind getrennte positive monotone Werte.
4. Einen eigenen HKDF-SHA-256-Document-Wrapping-Key aus dem DMK ableiten und
   den Document-Key in einem integrierten `DocumentKeyEnvelopeV1` per
   AES-256-GCM schützen. Envelope-AAD bindet Payload-Binding, Dokumentkontext,
   DMK und Envelope-Revision.
5. Das kanonische verschlüsselte Manifest erzeugen. Es bindet Dokument- und
   Storage-ID, Generationen, technischen Kontext, Originalname, MIME-Typ,
   Klartextgröße/-hash, Chunkvertrag, Erstellungszeit und App-/Formatversion.
6. Magic, längenbegrenzten kanonischen Header, Manifestrecord und
   Dokumentchunks streamend in eine neue versteckte Retained-Datei schreiben.
   Eigene Record-AAD bindet Payload-Digest, Dokumentkontext, Manifestdigest,
   Ordinal, Chunkindex und erwartete Größe.
7. Genau einen leeren Secretstream-`TAG_FINAL`-Record schreiben, Datei
   synchronisieren, schließen, Verzeichnis synchronisieren und den Container
   vollständig neu öffnen und verifizieren.
8. Erst den verifizierten Retained-Stand per atomarem No-Clobber-Hardlink unter
   dem opaque Zielnamen veröffentlichen, das Verzeichnis erneut
   synchronisieren und das veröffentlichte Ziel vollständig erneut
   verifizieren.
9. Erst danach Erfolg melden. Quelle und bestehende Ziele bleiben unverändert;
   vor dem Hardlink existiert kein sichtbarer Zielcontainer.

### Headerprüfung, Verifikation und Reader

Die Headerprüfung liest nur Magic, Längenrahmen und kanonischen sichtbaren
Header und schreibt nichts. Vollverifikation öffnet den Container no-follow,
prüft Format, Algorithmen, erwarteten Dokument-/Installationskontext,
Envelope, Manifest, Recordreihenfolge, Final-Tag, physisches EOF,
Klartextgröße/-hash und unveränderte Containeridentität.

Der kontrollierte Reader führt zuerst eine vollständige schreibfreie
Verifikation ohne Klartextausgabe aus. Danach entschlüsselt er denselben
erwarteten Container sequenziell erneut. Ausgegebene Chunks gelten bis zum
erfolgreichen `finish` nach Final-/EOF-/Hash- und Identitätsprüfung als
vorläufig; jeder Fehler ruft `abort` auf und darf nicht als Erfolg behandelt
werden. Secretstream v1 bietet kein Seek/Random Access.

### Bewusster synthetischer Export

Export ist nur ein expliziter isolierter Methodenaufruf. Nach vollständiger
Vorabverifikation wird ein neuer, exklusiver, no-follow Klartextstand unter
`exports` versteckt geschrieben, synchronisiert, gegen Manifestgröße und
-hash geprüft und per plattformspezifisch atomarem No-Clobber-Rename
veröffentlicht. Erst danach wird Erfolg gemeldet. Eigene unvollständige
Tempinhalte werden bei normalen Fehlerpfaden ausschließlich über den noch
offenen, identitätsgebundenen eigenen Deskriptor geleert; es gibt keinen
pfadbasierten Cleanup-Unlink. Der leere Retained-Dateieintrag bleibt
analysierbar. Ein harter Prozessabbruch vor dem Rename kann eine versteckte,
eindeutig nicht veröffentlichte Retained-Datei ausschließlich im
markergebundenen Exportroot hinterlassen. Sie gilt nie als erfolgreicher
Export. Vorhandene, symlinkende oder fremde Ziele bleiben unverändert. Es gibt
keine automatische Öffnung oder Vorschau. Ein späteres Produkt muss deutlich
anzeigen, dass der Export außerhalb der App unverschlüsselt ist, und benötigt
eine eigene Restart-/Cleanup-UX.

### Austausch und Rotation

- Dokumentaustausch erzeugt eine vollständig neue Dokumentgeneration mit
  neuem Storage-, Container- und zufälligem Document-Key. Erst nach
  vollständiger Verifikation darf ein injizierter Pointer-Switch als
  erfolgreich simuliert werden. Bei Fehlschlag bleibt die alte Generation
  maßgeblich und nutzbar.
- DMK-Schutzwechsel rewrappt denselben Document-Key mit frischer Nonce und
  höherer Envelope-Revision in eine neue No-Clobber-Containerdatei. Der
  verschlüsselte Payload wird unverändert kopiert, anschließend unter dem
  neuen DMK vollständig verifiziert und erst dann für einen Pointer-Switch
  angeboten. Keine Datei wird in-place geändert.
- Datenrotation erzeugt einen neuen zufälligen Document-Key, erhöht dessen
  Generation und verschlüsselt den gesamten Payload in einen neuen Container.
  Der Sprint-10-Writer stellt dieses isolierte Primitive mit expliziter
  Key-Generation bereit; eine produktive Pointer-/Rotationsoperation ist nicht
  aktiviert. Die Datenrotation ist von einem reinen DMK-Rewrap und von einem
  inhaltlichen Dokumentaustausch getrennt.
- Der Austauschprototyp bestätigt die vorbereitete Generation unmittelbar vor
  dem simulierten Pointer-Switch erneut. Nur ein eindeutig erfolgreicher
  Callback liefert die vorhandene Retained-Hardlink-Evidenz der alten
  Generation im Ergebnis; bei Callback-Ausnahme ist der Umschaltzustand
  ausdrücklich unbekannt und muss ein späteres Produkt transaktional
  rekonstruieren.

### Retained, Quarantäne und GC

`ACTIVE`, `PREPARED`, `RETAINED`, `QUARANTINED` und `GC_ELIGIBLE` sind
technische Lifecyclezustände des isolierten Inventars. Ein Neustartscan ist
read-only, folgt keinen Symlinks und klassifiziert ausschließlich bekannte
Containerformen. Unbekannte, ungebundene, beschädigte oder kontextfremde
Dateien werden niemals automatisch gelöscht. `GC_ELIGIBLE` setzt eine
explizite bekannte Retained-Allowlist, erfolgreichen Bestandsabgleich und
vollständige Verifikation voraus. Sprint 10 liefert nur einen Dry-Run und
behauptet keine sichere physische Löschung.


## Security Sprint 9 - isolierter Backupcontainer-Lifecycle

1. Der injizierte private Test-Root, DMK, technische Kontext und synthetische
   Quellen werden vor dem Schreiben geprüft.
2. Der Writer erzeugt einen zufälligen Backup-Key, schützt ihn per
   HKDF-SHA-256-Backup-Wrapping-Key und AES-256-GCM-Envelope und schreibt einen
   versionierten Secretstream-Recordstrom.
3. Der Verifier authentifiziert Header, Envelope, Manifest, Recordreihenfolge,
   Größen, Hashes, Final-Tag und EOF ohne Extraktion.
4. Restore erfolgt erst nach vollständiger Verifikation in einen neuen,
   exklusiv erzeugten synthetischen Root; der bestehende Produkt- und
   `.jkmbackup`-Lifecycle wird nicht verwendet.

## Security Sprint 7B - Authentisierte Lock-, Preflight- und Crossbinding-Lebenszyklen

Die Locktransitionen folgen ausschließlich dieser Zustandsmatrix:

| Vorzustand | Erlaubter Folgezustand |
|---|---|
| kein Eintrag | `ACQUIRED` |
| `ACQUIRED` | `RELEASED`, `STALE_DETECTED`, `BLOCKED` |
| `RELEASED` | `ACQUIRED`, `BLOCKED` |
| `STALE_DETECTED` | `TAKEOVER_PREPARED`, `BLOCKED` |
| `TAKEOVER_PREPARED` | `TAKEOVER_COMMITTED`, `BLOCKED` |
| `TAKEOVER_COMMITTED` | `RELEASED`, `STALE_DETECTED`, `BLOCKED` |
| `BLOCKED` | kein Folgezustand |

Jeder Eintrag trägt Sequenz, Vorgängerdigest, HMAC, Installation,
Datenbankkontext, Migration, Owner sowie Replay-Anker-, Journal- und
Artefaktevidenz. Das Repository publiziert nur den nächsten nummerierten
Eintrag mit Create-exclusively, Datei-`fsync` und Verzeichnis-`fsync`.
Laden und Fortsetzen verlangen den erwarteten Head-Digest samt Sequenz.

Der vollständige Kontextdigest bindet den echten Lockkopf. Der HMAC-Lockeintrag
bindet einen nicht zirkulären Digest aller übrigen Kontextfelder. Kein
Bestandteil kann unabhängig ausgetauscht werden.

Der Preflight ist rein, read-only und wiederholbar. Adapter liefern
authentisierte Anchor-, Registry-, Journal-, Lock- und Artefaktprojektionen.
Die Domain prüft IDs, Generationen, Revisionen, reale Quelldigests,
Dateiidentitäten, Capabilities, Versionen und phasengerechte Rollen. Freie
Backup-/Zielrollen ergeben `NEW`; fortsetzbare Phasen `RESUME`,
crashkritische Phasen `RECOVERY`, konsistenter Abschluss `COMPLETED`.
Jede Abweichung ergibt `BLOCKED`.

Diese Lebenszyklen führen keine Migration aus und verändern keine Produkt-,
Startup-, Login-, UI- oder Backup/Restore-Pfade.

## Security Sprint 6 - Anchor-, Lock- und Prototype-Recovery-Lifecycle

Der externe Anchor-Lifecycle lautet:

```text
kein Security-Bestand + kein Anker
-> initialize(context, revision 1)
-> read + verify
-> compare(current registry/journal)
-> atomisches advance um genau eine freigegebene Revision
-> read-after-write + verify
```

Initialisierung ist nur ohne vorhandene Security-Artefakte zulässig. Der
committed Snapshot bindet zusätzlich Database-Context, DMK-/Keyset-ID und
-Generation sowie die exakten SHA-256-Digests der bereits HMAC-
authentisierten Registry und des bereits HMAC-authentisierten Journals. Bei
vorhandener Envelope-Registry oder vorhandenem Migrationsjournal führen ein
fehlender, beschädigter, kontextfremder, rückläufiger oder unplausibel
vorspringender Anker sowie ein wiederverwendeter Revisionswert zu `blocked`.
Blockierung wird nicht automatisch zurückgesetzt. Registry und Journal werden
erst als aktueller Stand akzeptiert, wenn Installation/Security-Context,
Registry-High-Water-Mark und Journal-/Migrationsgeneration mit dem externen
Anker konsistent sind. Der Anker wird niemals vorgezogen, solange die zu
bindende Dateioperation oder ihre dauerhafte Journalpublikation nicht bewiesen
ist.

Ein Cross-Store-Advance folgt verbindlich diesem Protokoll und wird während der
gesamten Folge durch den exklusiven Migrations-Lock serialisiert:

```text
Lock-Owner prüfen
-> Anchor-prepare: alten committed Snapshot und exakt geplanten neuen Snapshot
   als pending mit geplanter Revision committed + 1 binden; committed Revision
   noch nicht vorziehen
-> Registry/Journal atomar extern publizieren und dauerhaft prüfen
-> beobachtete authentisierte Digests neu bilden
-> nur bei exakter Gleichheit mit pending: Anchor-commit auf exakt die geplante
   Revision
```

Nach Crash gelten genau drei Fälle. Entsprechen beide beobachteten Digests und
Bindungen exakt dem alten committed Snapshot, darf pending ausschließlich über
`abort_pending(expected, observed_committed)` verworfen werden. Dabei bleibt
der committed Artifact-Snapshot erhalten, pending wird entfernt und die
vorbereitete höhere Anchor-Revision wird als monotoner Abbruchnachweis
übernommen. Entsprechen die beobachteten Artefakte exakt dem pending Snapshot,
darf Commit fortgesetzt werden. Jeder Mischstand, unbekannte
Digest oder Kontextwiderspruch führt zu `blocked`. Prepare reserviert genau die
nächste Revision im pending Snapshot; Commit oder Abort übernehmen genau diese
Revision. Keine Operation setzt den Anker zurück oder verwendet eine Revision
erneut. Der Lock verhindert parallele Advances desselben
Datenbankkontexts aus verschiedenen Prozessen.

Der Lock-Lifecycle lautet:

```text
Root und Zielkontext prüfen
-> database-migration-v1.lock mit exklusiver Create-Semantik anlegen
-> Inhalt, Rechte und Dateiidentität zurücklesen
-> vor jeder Operation verify_owner
-> Operation und Journal-/Anchor-Prepare/Publish/Commit-Schritt ausführen
-> Eigentum und Dateiidentität erneut prüfen
-> kontrolliert release
```

Ein zweiter Prozess, ein fremder Owner, ein Symlink, eine ausgetauschte oder
manipulierte Datei und ein Pfad außerhalb des freigegebenen Test-Roots
blockieren. PID allein ist kein Eigentumsbeweis. Ein stale Lock darf nur nach
belastbarer Prüfung von Prozessstartidentität, Nonce, gespeicherter
Dateiidentität und Journalzustand ausdrücklich übernommen werden; ein
uneindeutiger Zustand bleibt bestehen und wird nicht automatisch überschrieben
oder gelöscht.

Die ausführende Prototype-Recovery beginnt mit einer rein verifizierenden
Auswertung. Vor jedem einzelnen Schritt werden Rootgrenze, Lock-Eigentum,
Journal-HMAC, Replay-Anker und die unmittelbar aktuelle Dateiidentität geprüft.
Zulässige Schritte sind ausschließlich:

1. ein verifiziertes Backup erneut prüfen;
2. ein eindeutig eigenes und unvollständiges SQLCipher-Testziel nach erneuter
   Identitätsprüfung in retained Quarantine verschieben;
3. Validierung eines identitätsgebundenen Testziels fortsetzen;
4. ein vollständig validiertes Testziel mit explizitem Key erneut öffnen;
5. bei authentisiertem `COMPLETED` plus
   `synthetic_prototype_completed` ausschließlich das evidence-gebundene
   SQLCipher-Testziel und das evidence-gebundene Backup kontrolliert in
   `.recovery-<role>-<migration_id>.quarantine` verschieben; bereits fehlende
   Rollen beziehungsweise ein exakt gebundener Quarantänerest werden
   idempotent als retained bestätigt, niemals gelöscht.

Kritische Schritte schreiben vor der Dateioperation einen authentisierten
Write-ahead-Zustand und danach einen neuen Beweis. Abbruch zwischen
Dateioperation und Journalupdate muss beim nächsten Aufruf eindeutig blockieren
oder anhand unveränderter Identitäten idempotent fortsetzbar sein. Die
Klartextquelle bleibt immer maßgeblich und wird niemals automatisch gelöscht,
umbenannt oder ersetzt. Anchor, Registry, authentisiertes Journal, Lock und
retained Quarantine bleiben auch nach terminaler Behandlung als Auditbeleg
erhalten. Reservierte
Swap-Phasen, unbekannte Dateien, fremde Tempdateien und widersprüchliche
Beweise führen ohne Dateioperation zu `blocked`.

Subprozessabbrüche, ENOSPC, fehlende Rechte, fehlgeschlagenes `fsync`,
fehlgeschlagene No-Clobber-Renames/Replace-Injektionen sowie Dateiwechsel zwischen Prüfung und Operation
werden ausschließlich an synthetischen temporären Daten injiziert. Nach jedem
Fehler bleiben Quelle und ein gültiges Backup erhalten; die ausdrücklich
autorisierte terminale `COMPLETED`-Behandlung verschiebt das exakt gebundene
Backup lediglich unter seinem retained Quarantine-Namen. Journal und Lock
bleiben auswertbar oder der Zustand blockiert. Recovery ruft für Ziel und
Backup kein pathname-basiertes `unlink` oder `remove` mehr auf; das frühere
finale Unlink-TOCTOU ist beseitigt. Die bekannte P2-Grenze ist ausschließlich
die retained Quarantine ohne freigegebenen handlebasierten
Bereinigungsprozess. Die Tests belegen keine vollständige
Power-Loss-Sicherheit.

Dieser Lifecycle ist keine Startup-Recovery, kein fachlicher Restore und kein
Authentifizierungsprozess. Passwortwechsel, Auth-Recovery-Codes, Touch ID,
Support-Reset, bestehendes Backup/Restore und `security.sqlite` bleiben
unverändert.

## Security Sprint 5 - Product-Key- und Journal-Lifecycle

Der isolierte Envelope-Lifecycle ist `create pending -> activate -> load
active -> revoke|fail`. Der Database-Key entsteht mit kryptografischem Zufall;
der DMK leitet per HKDF-SHA-256 und der festen Domain
`jenaplan-kompetenzmanager/database-key-wrap/v1` einen flüchtigen
Wrapping-Key ab. Database-Context, Key-Generation und monotone
`rewrap_revision` sind KDF-Kontext. Eine zweite getrennte HKDF-Domain erzeugt
den flüchtigen HMAC-Key für die komplette Registry. Jeder Statuswechsel versiegelt denselben
Database-Key mit einem revisionsverschiedenen AEAD-Key-Kontext und neuer
96-Bit-Nonce. Die Registry hält Context und Generations-High-Water-Mark auch
nach idempotenter Entfernung terminaler Envelope-Metadaten; beim aktuellen
authentisierten Registry-Stand wird eine Generation nie erneut vergeben.
HMAC-SHA-256 bindet dabei auch Context,
High-Water-Mark, leere Envelope-Liste und Mitgliedschaft. Beschädigte,
unbekannte oder mehrdeutige Registrys
werden weder ersetzt noch neu erzeugt.

Der Journal-Lifecycle schreibt vor jeder kritischen Phase einen atomaren
Zustand und danach den Abschlussbeleg. Die erlaubte Hauptkette ist:

```text
not_started -> preflight_started -> source_verified
-> backup_started -> backup_created -> backup_verified
-> target_creation_started -> target_created
-> export_started -> export_completed
-> validation_started -> validation_completed
-> reopen_started -> reopen_verified -> completed
```

`failed`, `blocked` und `completed` sind terminal. Rollback ist nur von
Ziel-/Export-/Validierungsphasen über `rollback_started -> rollback_completed
-> failed` erlaubt. Swap-Phasen sind für spätere Versionen reserviert und
führen in Sprint 5 stets zu manueller Blockierung, weil noch keine
Rename-Topologie persistiert wird. Prüf-Codes wachsen monoton.
Reservierte Pflichtchecks stammen aus einer festen Allowlist, dürfen erst mit
der zugehörigen erreichten Phase erscheinen und Journalzeitpunkte sind monoton.

Jeder Journalstand bindet Migration-ID, Database-Context,
Database-Key-ID/-Generation und DMK-Key-ID/-Generation. Quelle, Backup und Ziel
werden durch sichere relative Rolle, `st_dev`, `st_ino`, Größe, SHA-256 und
schwaches `mtime_ns` belegt. Fehlender Beleg, fremde ID, Hashabweichung,
Symlink, Temp-Rest, ungültige Historie, falsche Version oder HMAC führen zu
`block_manual_review`. Bei `rollback_started` bedeutet das eigene noch
vorhandene Ziel `rollback_target`; sein nachweisliches Fehlen nach bereits
erfolgter Löschung bedeutet `no_action`. Die Entscheidung führt selbst keine
Dateioperation aus und löscht niemals die Klartextquelle.

Persistenz erfolgt über Tempdatei, Flush, Datei-`fsync`, `os.replace` und auf
POSIX Verzeichnis-`fsync`; Create nutzt exklusives Link-Publizieren. Ein
übriggebliebenes Tempfile blockiert. Vollständige Stromausfallsicherheit,
Rollbackschutz gegen das Zurückspielen einer alten gültigen Registry oder
eines alten gültigen Journals und
physisch sicheres Löschen werden nicht behauptet. Windows bleibt bis zu ACL-,
Reparse-Point-, handlebasierter File-ID-, Replace-/Sharing- und Crashabnahme
gesperrt.

Der synthetische Sprint-4-Pfad führt vor jedem Sidecar-Schreiben erneut
Workspace-, Guard- und Integritäts-Preflight aus. Nur danach werden Envelope
und Journal angelegt und der entschlüsselte flüchtige Database-Key an den
SQLCipher-Testprovider übergeben. Es gibt keine Startup-, Login-, UI-,
Backup/Restore- oder Produktintegration.

## Security Sprint 4 - isolierter Migrations- und Rollback-Lifecycle

1. Ein Test erzeugt einen neuen temporären Root, eine deterministische
   synthetische Fixture und einen zufälligen flüchtigen 32-Byte-Database-Key.
2. Die Engine prüft Root/Pfadtrennung, reguläre Datei, Symlinkfreiheit,
   Guard-Wert, Application-ID, User-Version, `integrity_check` und
   `foreign_key_check`; anschließend wird der Quell-Dateihash fixiert.
3. Die SQLite-Backup-API erzeugt ein separates Backup. Integrität, Tabellen,
   Zeilen, PK/FK, Trigger, Views, Indizes, PRAGMAs, Schemahash und Datenhash
   müssen vor dem Export der Quelle entsprechen.
4. `SQLCipherConnectionProvider` erzeugt ein leeres Ziel. Die Quelle wird
   read-only/immutable mit leerem Attach-Key angehängt; `sqlcipher_export`
   überträgt in einer expliziten Transaktion Schema und Daten. Persistente,
   nicht automatisch übertragene PRAGMAs werden explizit gesetzt.
5. Nach Commit und `fsync` wird das Ziel geschlossen und über den normalen
   SQLCipher-Provider neu geöffnet. Dadurch laufen Cipher-, SQLite- und
   Fremdschlüsselintegrität erneut.
6. Die Vergleichskomponente bildet Quell- und Zielsnapshot. Jeder Wert erhält
   einen SQLite-Typmarker und eine Längenrahmung; sortierte Zeilenhashes pro
   Tabelle bilden zusammen den globalen Datenhash. Die persistente interne
   AUTOINCREMENT-Fortsetzung aus `sqlite_sequence` ist ausdrücklich enthalten.
   Nur vollständige Gleichheit aller registrierten Dimensionen gibt das Ziel
   frei.
7. Der Quell-Dateihash wird erneut geprüft. Der Prototyp meldet Größen und
   Laufzeiten und entfernt nach dem Lauf den gesamten temporären Root.

Rollback bei Backupfehler entfernt nur ein eigenes Teilbackup. Rollback nach
erfolgreichem Backup behält dieses Backup, entfernt ein eigenes fehlgeschlagenes
Cipher-Ziel nur bei gleicher Dateiidentität und prüft Quelle sowie Backup
erneut. Weil kein Live-Austausch stattfindet, bleibt die Quelle zu jeder Zeit
maßgeblich.

Ein späterer Live-Lifecycle benötigt exklusiven App-Lock, dauerhaftes Journal,
ausreichend reservierten Speicher, `fsync` von Datei und Verzeichnis,
retained rollback source, atomaren Rename und eindeutige Start-Recovery vor
Öffnung der fachlichen Runtime. Diese Schritte sind nur dokumentiert.

## Security Sprint 3 - Isolierter SQLCipher-Test-Lifecycle

1. Ein Test oder technischer Smoke erzeugt ein neues temporäres Verzeichnis
   und 32 zufällige Schlüsselbytes im Arbeitsspeicher.
2. `SQLCipherConnectionProvider` lädt den expliziten optionalen Treiber, prüft
   dessen Cipher-Version und legt ausschließlich eine neue Testdatei an.
3. Der rohe 256-Bit-Testschlüssel wird als erste SQLCipher-Operation gesetzt;
   danach folgen feste Memory-, Foreign-Key-, Journal-, Sync- und Temp-Regeln.
4. Der Test schreibt nur synthetisches Schema und synthetische Daten, committet
   beziehungsweise rollt kontrolliert zurück und schließt jede Verbindung.
5. Wiederöffnen mit dem richtigen Schlüssel prüft
   `cipher_integrity_check`, `integrity_check`, Schema und Zeilenanzahl.
   Klartext-SQLite, falscher Schlüssel, fehlende Engine und beschädigte Datei
   werden ohne Fallback, Neuerstellung oder Überschreiben abgewiesen.
6. Der normale `sqlite3`-Treiber muss die Datei ablehnen; zusätzlich wird
   geprüft, dass der synthetische Marker nicht als Klartext in der Datei liegt.
7. Nach Ende des Smokes wird das gesamte temporäre Verzeichnis entfernt.

Der Produkt-Lifecycle ruft diesen Pfad nicht auf. Eine spätere Migration muss
die Anwendung exklusiv sperren, ein verifiziertes unverändertes Backup
erzeugen, Quelle und separates Cipher-Ziel prüfen, fachliche Invarianten und
Anhänge berücksichtigen, atomar austauschen und bei jedem Fehler rollback- oder
fortsetzungsfähig bleiben. Das Entlinken beziehungsweise Überschreiben einer
Klartextdatei garantiert auf SSD/APFS/NTFS wegen Copy-on-write,
Wear-Leveling, Snapshots und Betriebssystem-Caches keine physische sichere
Löschung.

## Security Sprint 2 - Data Master Key Lifecycle

Der Lifecycle wird nur durch einen expliziten Entwicklungsaufruf gestartet;
Startup und Runtime rufen ihn nicht auf.

1. Der Zufallsgenerator erzeugt genau 32 Bytes und eine neue Key-ID.
2. Aus dem DMK entsteht ein SHA-256-Fingerprint; der Sidecar schreibt nur ein
   `pending`-Keyset mit Generation und technischen Metadaten.
3. `DataMasterKeyStore` schreibt den DMK unter Installations- und Key-ID-Bindung
   in den Plattformstore.
4. Erst danach wird das Keyset `active`. Bei Neustart wird ein passender
   `pending`-Eintrag gelesen, auf Länge und Fingerprint geprüft und fortgesetzt.
5. Laden liest ausschließlich über Key-ID und Installation, prüft 32-Byte-Länge
   und Fingerprint und gibt Material nur flüchtig an den Aufrufer zurück.

Fehlende oder beschädigte Schlüssel werden `failed` und niemals still neu
erzeugt. Weil der Development-Sidecar noch nicht authentifiziert ist, löscht
eine Längen- oder Fingerprintabweichung den Plattform-DMK nicht automatisch;
Bereinigung erfordert den expliziten Lösch-Lifecycle. Falsche Bindung liefert
`not_found`; verweigerter Zugriff und temporäre
Plattformfehler bleiben retry-fähig. Widerruf setzt zuerst `revoked` und löscht
danach den Plattformwert. Bleibt die Löschung aus, wird sie anhand terminaler
Metadaten beim nächsten expliziten Löschaufruf erneut versucht.

Ein Passwortwechsel betrifft ausschließlich den bestehenden Auth-Lifecycle und
ruft keine DMK-Operation auf. Unbekannte Sidecar- oder Envelope-Versionen werden
abgewiesen, nicht migriert. Es gibt keine automatische Startup-Aktion, keine
Migration, keinen Pilotdatenzugriff und keine fachliche Verschlüsselung.

## Sprint 0.2S.1 - Grafischer Offline-Supportablauf

```text
bewusste .jkmresetrequest-Auswahl
-> kanonische Requestprüfung ohne Dateisuche
-> datensparsame Projektion und flüchtiger Installationsname
-> aktiven öffentlichen support-2026-b samt gekürztem Fingerprint zeigen
-> bewusst gewählten externen verschlüsselten Privatschlüssel entsperren
-> Public-Key-Gleichheit prüfen
-> unveränderten JKM-SR1-Code über den bestehenden Generator erzeugen
-> minimales technisches Audit schreiben
-> nur auf Klick kopieren oder exklusiv als .jkmresettoken mit 600 speichern
```

Ungültige, noch nicht gültige oder abgelaufene Requests brechen vor
Schlüsselzugriff ab. Ein falscher, unverschlüsselter, zu offen berechtigter oder
nicht zur Produktregistry passender Schlüssel erzeugt keinen Token und keinen
Erfolgsaudit. Die Passphrase bleibt ausschließlich im Arbeitsspeicher des
laufenden Vorgangs. Es gibt keine automatische Übertragung und keine
automatische Ausgabedatei.

Der sichtbare Installationsname ersetzt keine Installations-ID und gelangt
weder in Request, Token noch Audit. Der Anfragecode ist nur eine telefonische
Referenz. Tokenformat, Signatur, Laufzeitgrenzen, App-seitige Prüfung,
Sicherheitsbackup und Resettransaktion bleiben byte- und verhaltensgleich.

## Sprint 0.2U.1 - App-Update ohne Zugriff auf Nutzerdaten

Der Updateclient ist ein reiner Distributionspfad und keine fachliche
Datenquelle. Er liest ausschließlich fest konfigurierte Updatekonfiguration,
authentisierten Appcast, Release-Metadaten und das signierte Appartefakt. Feed,
Release Notes und Updatezustand enthalten keine Schüler-, Schul-, Dokument-,
Konto-, Installations- oder Gerätecredentialdaten. Es gibt keine Telemetrie und
keinen Upload aus der lokalen Runtime.

```text
bewusste Prüfung
-> signierten HTTPS-Appcast authentisieren
-> Version, Build, Kanal, macOS und arm64 prüfen
-> EdDSA-signiertes Artefakt laden und vor Entpacken verifizieren
-> sicheren Installationszeitpunkt durch Shell bestätigen
-> ausschließlich geschlossenes .app-Bundle atomar ersetzen
-> neue App gegen unveränderte externe Runtime starten
```

Ausgeschlossen sind `kompetenzmanager.sqlite`, `documents/`, `exports/`,
`backups/`, `logs/`, `security/security.sqlite`, Enrollment-Marker,
`app-preferences.json` und macOS-Keychain. Das Update erzeugt, kopiert, migriert,
sichert, löscht oder repariert keinen dieser Bestände. Offene Worker und
ungespeicherte Arbeitsstände verschieben Installation und Relaunch. Ein Fehler
vor dem atomaren Austausch lässt App und Runtime unverändert; ein Fehler beim
nächsten Start darf keine stille Datenreparatur auslösen.

Historisch blieb Version `0.2.2` fach- und security-schemaidentisch zu `0.2.1`. Der
Security Store besitzt seinen bestehenden kontrollierten Migrationsvertrag;
für die fachliche SQLite existiert noch kein allgemeiner Update-Migrations- und
Rollbackvertrag. Ein späteres schemaänderndes Update benötigt deshalb vorab
einen eigenen dokumentierten Lifecycle. Der zulässige manuelle Rollback gilt
nur zwischen schemaidentischen, signierten/notarisierten Appversionen.

Laura hat `0.2.0` nicht installiert und beginnt direkt mit der manuell
installierten, ad-hoc-signierten `0.2.1`. Ab dieser Version kann sie den festen
Pilot-Appcast ausschließlich bewusst prüfen. `0.2.2` ist das erste
beaufsichtigte Folgeupdate und ersetzt nur das geschlossene App-Bundle. Stable
und ein produktiver Updatekanal bleiben deaktiviert. Keychain- und
Touch-ID-Verhalten beim ersten realen Update auf Lauras Mac bleibt eine offene
Pilotprüfung.

## Sprint 0.2B.6 - Schlüsselbereitstellung, Signatur und Supportpaket

Provisionierung wird ausschließlich durch den getrennten Finder-Starter bewusst
ausgelöst. Der Support-Verantwortliche wählt ein Verzeichnis außerhalb jedes
Repositorys; es erhält `700`, der private Ed25519-Schlüssel wird direkt als
passphrasenverschlüsseltes PKCS#8 mit `600` publiziert. Die separat publizierte
öffentliche Beschreibung enthält `key_id`, Erstellungszeit, vorgesehenen Status
und Fingerprint. Es gibt keinen Klartextschlüssel und keine automatische
Registry-Änderung.

Die Registry-Aktivierung ist ein eigener App-Release. Das strikt versionierte
Manifest wird beim Import deterministisch validiert; unbekannte Felder,
Versionen, Algorithmen, Schlüsselgrößen, Base64url-Darstellungen, Fingerprints,
Zeiten, IDs, Duplikate und Lebensdauern brechen fail-closed ab. Ohne bewusst
eingetragenen öffentlichen PO-Schlüssel bleibt `product_enabled = False`.
`active` und kurzzeitig `retiring` verifizieren; `retired`, `revoked`, unbekannt,
noch nicht gültig und abgelaufen werden abgelehnt.

Version `0.2.2` aktiviert nach getrennter Product-Owner-Fingerprintfreigabe
genau den öffentlichen Schlüssel `support-2026-b`. Der private Schlüssel und
die Passphrase bleiben extern und getrennt. Recovery-Code bleibt der erste Weg;
der Support-Reset ist der betreute Ausnahmeweg. Die technische Anfrage enthält
keine Schülerdaten, und das neue Passwort wird ausschließlich von der Lehrkraft
beim Folgestart gesetzt.

Der Support-Starter bestimmt seinen eigenen Ort und startet ausschließlich die
interaktive Offline-Laufzeit. Diese liest eine bewusst gewählte Datei oder einen
eingefügten Anfrageblock, zeigt nur technische Projektionen, verlangt die
Gerätebestätigung, prüft verschlüsselten privaten Schlüssel gegen die
öffentliche Beschreibung und liest die Passphrase höchstens dreimal verdeckt
über Python `getpass`. Nur 15/30/60/120 Minuten sind zulässig. Der Token wird
mit exklusiver Neuanlage und `600` am bewusst gewählten Ziel publiziert; Ausgabe
im Terminal erfolgt nur nach separatem `JA`. Kein Schritt öffnet fachliche
SQLite, Backups oder Dokumente.

Das Supportpaket wird separat vom App-/Laura-Build aus zwei arm64-Onefile-
Executables und einer festen Allowliste erzeugt. Prüfsummen, ZIP-Struktur,
Dateirechte, lokale Pfade und Secretmuster werden nach erneutem Entpacken
verifiziert. Der App-/DMG-/Laura-Build ruft diesen Prozess nicht auf.

## Sprint 0.2R - Release-Build und Übergabe

Der Release-Build entfernt seine bekannten Build- und macOS-Ausgabeverzeichnisse,
erzeugt den `release`-Payload ohne Startdaten, baut Security-Bridge, App und DMG
frisch, signiert ad hoc sofern keine Developer-ID verfügbar ist, verifiziert die
Signatur und erzeugt Dokumente, Prüfsummen und Inventar aus kanonischen Quellen.

Die leere Pilotvariante wird ausschließlich aus diesen aktuellen Ausgaben und
der bestehenden kanonischen Testmappe zusammengestellt. Für die getrennte
Laura-Testdatenvariante erzeugt `scripts/build_laura_testdata_backup.py` in
einer isolierten temporären Runtime den bestehenden deterministischen
Acht-Monats-Seed und transportiert ihn ausschließlich über
`BackupApplicationService` in `Laura-Testdaten-0.2.0.jkmbackup`. Das Archiv
wird anschließend über Backup- und Restore-Vertrag vollständig verifiziert.
Beide ZIPs enthalten dasselbe leere DMG; nur die Laura-Testdatenvariante enthält
das separate Backup. Die interne `SHA256SUMS.txt` bindet jeweils alle
enthaltenen Dateien. Entpacken, Inhaltsliste, Dokumentöffnung, Mappe, DMG und
Restore-Vorschau werden anschließend geprüft. Build- und Übergabeartefakte
schreiben weder fachliche noch Security-Daten in eine produktive Runtime zurück.

Laura richtet beim Erststart zunächst ausschließlich ihr lokales Konto ein und
stellt das Testdatenbackup danach über `Einstellungen > Datensicherung` und den
normalen bestätigten Restore-Weg wieder her. Konto, Security Store,
Recovery-Codes, Gerätecredentials und AppPreferences bleiben lokal erhalten und
werden vom fachlichen Restore weder geliefert noch ersetzt.

Reale Testresultate werden nur nach tatsächlicher Durchführung in der
Testmappe erfasst. Offene Hardware-, Produktivschlüssel-, Signierungs- und
Notarisierungsprüfungen bleiben offen.

## Sprint 0.2B.5 - Sichtbarer Support-Reset und Betriebsprozess

1. Nutzer erzeugt lokal genau eine aktive technische Anfrage; eine neue widerruft
   die vorige. Kopieren oder `.jkmresetrequest`-Export erfolgt nur bewusst.
2. Nutzer übermittelt ausschließlich diese Anfrage. Support prüft Identität
   organisatorisch und signiert extern mit verschlüsseltem Privatschlüssel.
3. Die App normalisiert nur äußere ASCII-Leerzeichen, begrenzt die Eingabe und
   prüft Envelope, kanonisches Payload, Key, Signatur, Installation, Nutzer,
   Anfrage, Nonce, Aktion, Zeiten, Status und Wiederverwendung. Die Vorschau
   konsumiert nichts.
4. Erst die ausdrückliche Bestätigung startet einen nicht abbrechbaren Worker.
   Der bestehende Backup-Service erzeugt ein neues `.jkmbackup` im kanonischen
   Backupziel und verifiziert die publizierten Bytes erneut.
5. Nur mit gültigem Proof konsumiert der Core Anfrage und Token-Digest atomar,
   ersetzt den Passworthash durch den Resetmarker, widerruft alle Recovery-Sätze
   und Gerätecredentials, neutralisiert Drosselungen, erhöht die Epoch und setzt
   `password_reset_pending`.
6. Desktop verdeckt die Fach-UI, verwirft die Sitzung, bereinigt Keychain-Reste
   best effort und beendet die App. Ein Löschfehler kann wegen Storestatus und
   Epoch nicht authentifizieren.
7. Der nächste Start erlaubt weder Passwortlogin noch Gerätecredential/Touch ID.
   Erst neues Passwort, neuer Recovery-Satz, einmalige Anzeige und bewusste
   Sicherungsbestätigung aktivieren Konto und neue Sitzung.

Fehler vor dem Security-Commit lassen Store, Anfrage und Token unbenutzt; ein
bereits erfolgreich erzeugtes Sicherheitsbackup darf erhalten bleiben. Der
Vor-Auth-Pfad liest die fachliche DB ausschließlich über den Backup-Service und
erzeugt keine AppShell oder Fachprojektion. Anzeigename, Onboardingstatus,
Fachdaten, Dokumentpfade und Restoreverträge werden nie verändert.

Audit im externen Supportprozess umfasst `key_id`, Anfrage-ID, Aktion,
Ausgabe-/Ablaufzeit, Supportbearbeiter und gekürzte Installations-ID. Die App
implementiert kein zentrales Audit, keine automatische Übertragung und keine Cloud.

## Sprint 0.2B.4a - Gerätecredential-Lebenszyklus

### Aktivierung

Aktivierung ist nur unmittelbar nach erfolgreicher Passwortanmeldung oder nach
erneuter aktueller Passwortbestätigung und ausdrücklicher Zustimmung zulässig.
Der Application Service erzeugt UUIDv4, 32 zufällige Secret-Bytes und 16 Byte
Salt und bildet `SHA-256(salt || secret)`. Zuerst wird ein nicht
authentifizierender `pending`-Datensatz geschrieben, danach das Secret im
Plattform-Store angelegt und erst zuletzt genau dieser Datensatz transaktional
aktiviert; dabei wird ein Vorgänger widerrufen. Scheitert ein Schritt, wird
`pending` widerrufen und das neue Secret best effort gelöscht. Beim nächsten
Start werden verbliebene `pending`-/`revoked`-Secrets bereinigt. Ohne aktiven
Storedatensatz kann ein Secret niemals authentifizieren; nach erfolgreichem
Commit wird ein verdrängtes altes Secret best effort entfernt.

### Start und Entsperrung

Restore-Recovery bleibt vor Auth. Erst am Auth-Gate lädt der Application Service
den aktiven Datensatz, prüft Status, Installation, Nutzer und aktuelle
Security-Epoch und liest anschließend das Secret. Die Verifikation erfolgt mit
konstantzeitnahem Vergleich. Nur ein vollständig passender Datensatz erzeugt
eine neue flüchtige Sitzung. Inkonsistenz, fehlendes Secret, Lesefehler, falscher
Hash oder Epoch-Abweichung widerrufen den Storezustand und führen zum Passwort;
es gibt keinen automatischen Credential-Neuaufbau und keine Fach-DB vor Auth.

Touch ID verlangt zusätzlich vor dem Secret-Lesen eine erfolgreiche echte
LocalAuthentication-Prüfung. Alle anderen Resultate lassen die Sperre bestehen
und den Passwort-Fallback unmittelbar verfügbar. Ein Abbruch erzeugt keinen
Dialogloop und keinen eigenen Biometrie-Fehlversuchszähler.

### Widerruf und Bereinigung

Explizite Deaktivierung, Passwortänderung, Recovery-Abschluss, Support-Reset,
Security-Store-Inkonsistenz und optionale Konto-Neueinrichtung markieren aktive
Credentials zuerst atomar `revoked`. Passwort-/Resetpfade erhöhen zusätzlich
die Security-Epoch. Keychain-Löschung erfolgt danach best effort; ein nicht
löschbarer Eintrag bleibt wegen Storestatus/Epoch unwirksam. Fehlende
Keychain-Einträge werden niemals rekonstruiert.

### Backup, Restore, Diagnose und App-Ende

Gerätegeheimnis und Credential-Metadaten sind vollständig von `.jkmbackup`
ausgeschlossen. Fachliches Restore verändert die Zielinstallation nicht. Ein
Runtime-Ordnerumzug oder Gerätewechsel ist nicht unterstützt. Diagnose und Logs
enthalten nur erlaubte Ereigniscodes ohne Secret, Hash, Salt, vollständige ID,
Passwort oder biometrische Geräteinformationen. Beim App-Ende endet nur die
In-Memory-Sitzung; das widerrufbare Credential kann am nächsten Auth-Gate eine
neue Sitzung erzeugen.

## Sprint 0.2B.4 - Kontoaufnahme, Authentifizierung und Sperre

Start: Nach Restore-Recovery werden nur Runtime-Root und `security/` sicher
vorbereitet. Store und Marker werden getrennt validiert. Erst `authenticated`
gibt die bestehende fachliche Runtime-Vorbereitung frei; vorher sind
Pilotdatenkopie, Produktordner, fachliche SQLite-Verbindung, Adapter,
`refresh_all()` und `AppShell` unzulaessig.

Erstkonto und Legacy-Aufnahme: Nur wenn Store und Marker gemeinsam fehlen,
wird anhand bereits vorhandener fachlicher Runtime-Artefakte zwischen
`first_run` und `legacy_enrollment` unterschieden, ohne die fachliche Datenbank
zu oeffnen. Passwort und zehn Codes werden vorbereitet. Der Account bleibt bis
zur ausdruecklichen Sicherungsbestaetigung `password_reset_pending`; erst die
atomare Bestaetigung aktiviert Konto und Recovery-Satz. Abbruch vor der
Bestaetigung gibt die fachliche App nicht frei. Store-/Marker-Asymmetrie ist
`inconsistent` und darf nicht neu aufgenommen werden.

Optionales App-Profil bei Kontoaufnahme: Erstkonto und Legacy-Aufnahme sammeln
`display_name` rein optional neben dem Security-Prozess. Die UI entfernt nur
aeussere Leerzeichen, wertet leere Eingabe als `null`, erhaelt internen
Unicode-Inhalt und begrenzt auf 80 Zeichen. Persistiert wird erst nach der
erfolgreich bestaetigten Kontoaktivierung atomar in `app-preferences.json`.
Fehler oder Verzicht beim Anzeigenamen veraendern weder Pending-/Crashvertrag
noch Account-Aktivierung, Recovery-Codes oder Freigabeentscheidung.

Login: Argon2-Verifikation laeuft ausserhalb des UI-Threads. Erfolg setzt
Fehlversuche zurueck, darf atomar rehashen und erzeugt eine neue fluechtige
Sitzung aus Kontobindung und aktueller Epoch. Fehler und Sperrzeiten bleiben
generisch; Secrets werden weder geloggt noch persistiert.

Recovery: Ein akzeptierter einmaliger Code setzt das Konto atomar auf
`password_reset_pending`; normaler Login ist danach gesperrt. Neues Passwort
und neuer Recovery-Satz werden vorbereitet, alte Saetze widerrufen und die
Epoch erhoeht. Erst die Bestaetigung der einmal gezeigten Codes aktiviert Satz
und Konto atomar. Ein Crash bleibt fortsetzbar in `password_reset_pending`;
altes Passwort und alte Codes geben die App nicht frei. Derselbe Abschluss gilt
fuer einen bereits erfolgten Support-Reset, ohne Token-Eingabe in der UI.

Passwortwechsel: Aktuelles Passwort, Policy und atomarer Hashaustausch werden
im Core geprueft. Fehlversuche werden neutralisiert und die Epoch wird in
derselben Transaktion erhoeht. Der bestehende Recovery-Satz bleibt erhalten;
die laufende Sitzung wird mit der neuen Epoch erneuert.

App-Profil aendern: Die Unterseite `Sicherheit` fuehrt den klar getrennten
Bereich `Persönliche Begrüßung`. Speichern normalisiert und validiert ueber
`AppPreferencesFile`, aktualisiert die Dashboard-Projektion und beruehrt weder
Security Store noch fachliche SQLite. Passwortwechsel, Recovery und
Support-Reset lesen oder schreiben `display_name` nicht. Fachliches Restore
ersetzt den Wert nicht; `.jkmbackup` nimmt ihn nicht auf.

Erste Schritte: Nach erfolgreicher Authentifizierung und Shell-Aufbau prueft
`OnboardingController` ausschliesslich den lokalen `AppPreferencesFile`.
`not_started` und `in_progress` koennen die ruhige Orientierung oeffnen;
`completed` und `dismissed` oeffnen nicht automatisch. Bestehende
Installationen ohne Onboarding-Felder werden als neue lokale Produkteinfuehrung
einmal `not_started` migriert. Weiter/Zurueck speichern atomar den aktuellen
Schritt, Ueberspringen speichert `dismissed`, Abschluss speichert `completed`.
Navigation aus der Ansicht nutzt nur vorhandene Shell-Routen und speichert keine
fachlichen Daten. Fachliches Restore, Passwortwechsel, Recovery und
Support-Reset veraendern den Onboarding-Status nicht.

Sperre: Der zentrale Session-Controller akzeptiert nur echte Tastatur-, Maus-,
Touch-/Trackpad- und relevante Fensteraktivierung. Timer, Worker,
Backupfortschritt, Refreshes und Hintergrundsignale sind keine Aktivitaet.
Manuelle Sperre wirkt sofort; Inaktivitaet nutzt 5/10/15/30/60 Minuten mit
Standard 15; Wake sperrt bei Fristueberschreitung oder unklarer Zeitbasis.
Fachliche Fenster werden unsichtbar gehalten, ohne In-Memory-Eingaben zu
speichern oder zu verwerfen, und nach Authentifizierung wiederhergestellt.

Backup/Restore unter Sperre: Ein laufendes Backup endet weiter; sein
Fortschritt und Ergebnis werden bis zum Entsperren nicht gezeigt. Eine noch
unbestaetigte Restore-Vorschau wird geschlossen und aus dem UI-State entfernt.
Ein bestaetigter Handoff/Worker laeuft weiter. Nach Restore-Recovery ist stets
eine neue Authentifizierung erforderlich.

## Signierten Support-Reset anfordern und atomar ausfuehren

Der Prozess wird nur durch explizite Qt-freie Application-Aufrufe aktiviert.
Import und normaler App-Start erzeugen weder Anfrage noch Token, Backup oder
Security-Aenderung. Sprint 0.2B.3 besitzt keine UI, Startblockade oder Sitzung.

Anfrage:

```text
SupportResetService.create_request
-> gebundenen Security-Zustand `ready` und aktives lokales Konto pruefen
-> zufaellige UUIDv4 `reset_request_id` und 32-Byte-Nonce erzeugen
-> hoechstens 24 Stunden Gueltigkeit festlegen
-> bisher aktive Anfrage atomar widerrufen
-> neue technische Anfrage atomar aktivieren
```

Die Anfrage enthaelt nur Formatversion, Installation, Nutzer, Anfrage-ID,
Nonce, Aktion und UTC-Zeitpunkte. Ein getrenntes Support-Werkzeug liest diese
technischen Werte, laedt einen passphrasengeschuetzten privaten Ed25519-PKCS#8-
Schluessel und erzeugt ein standardmaessig 30 Minuten, maximal zwei Stunden
gueltiges `JKM-SR1`-Token. Private Schluessel, Passphrase und Klartext werden
weder geloggt noch in die App oder Registry uebernommen.

Pruefung und Reset:

```text
SupportResetService.execute
-> Groesse, Envelope/Version und striktes Base64url pruefen
-> kanonisches UTF-8-JSON, feste Felder/Reihenfolge/Typen und Algorithmus pruefen
-> oeffentlichen Key-Status und -Gueltigkeit pruefen
-> Ed25519-Signatur ueber exakt die kanonischen Payloadbytes pruefen
-> Installation, Nutzer, Anfrage, Nonce und Aktion binden
-> Tokenzeit mit zwei Minuten Toleranz und maximal zwei Stunden pruefen
-> Token-Digest und aktive einmalige Anfrage read-only vorpruefen
-> vorhandenen Backup-Service aufrufen
-> neues fachliches `.jkmbackup` vollstaendig erzeugen und verifizieren
-> erst danach eine `BEGIN IMMEDIATE`-Security-Transaktion starten
-> Anfrage und Token-Digest verbrauchen
-> alten Passworthash in einen nicht verifizierbaren Reset-Marker ersetzen
-> Konto auf `password_reset_pending` setzen
-> aktive und vorbereitete Recovery-Saetze samt Codes widerrufen
-> Login-/Recovery-Fehlversuche und Sperren neutralisieren
-> Security-Epoch monoton erhoehen und technischen Aenderungszeitpunkt setzen
```

Jeder Erstellungs-, Verifikations-, Port- oder Backupfehler bricht vor der
Security-Transaktion ab. Konkurrenz kann nur eine Anfrage/Token-Kombination
verbrauchen. Das Sicherheitsbackup verwendet unveraendert `.jkmbackup`; der
Security Store bleibt ausgeschlossen. Fachliche Datenbank, Dokumente, Backups,
IDs und Restore-Vertraege werden nicht migriert oder veraendert.

Anfrage und Token sind nicht vor `created_at` und nicht nach `expires_at`
gueltig. Zwei Minuten Toleranz dienen ausschliesslich begrenztem Clock Skew;
eine manipulierte oder stark falsche Offline-Uhr bleibt ein Restrisiko.
Unbekannte Version, Aktion, Algorithmus, unbekannte/widerrufene/nicht gueltige
Schluessel, nicht kanonische Payloads und Wiederverwendung werden ohne Fallback
abgelehnt. Nach Erfolg sind altes Passwort, alte Recovery-Codes und dasselbe
Token unwirksam.

Die Security-Epoch ist der spaetere Widerrufsanker fuer gespeicherte
Anmeldungen. `Auf diesem Geraet angemeldet bleiben`, Geraete-/Sitzungstokens,
Keychain und optionales Touch ID folgen erst in eigenen Sprints;
Inaktivitaetssperre und Passwort-Fallback bleiben dann verbindlich.

## Security Store feststellen und initial einrichten

Der Security Core wird nur durch einen expliziten Application-Aufruf aktiviert;
Import, normaler App-Start und fachliche Datenbankinitialisierung erzeugen
weder Store noch Marker. Der aktuelle produktive Start bleibt in Sprint 0.2B.2
ohne Authentifizierungsblockade.

Zustandsvertrag vor jeder Operation:

- Store und Marker fehlen: `uninitialized`.
- Store und Marker sind vorhanden, streng valide und gebunden: `ready` oder `password_reset_pending`.
- Marker vorhanden, Store fehlt oder ist unbrauchbar: fail-closed `inconsistent`/`corrupt`.
- Store vorhanden, Marker fehlt oder stimmt nicht: fail-closed `inconsistent`; keine stille Reparatur.
- unbekannte neuere Schema-/Formatversion: fail-closed `unsupported_version`.

Initiale Einrichtung:

```text
SecurityApplicationService.enroll_local_account
-> Passwort-Policy pruefen
-> IDs, Markerreferenz und 10 Recovery-Codes aus injizierter Zufallsquelle erzeugen
-> Argon2id-Hash und ausschliesslich gesalzene Recovery-Hashes berechnen
-> SQLiteSecurityRepository erzeugt und validiert einen temporaeren Store
-> Storetransaktion committen, fsyncen und atomar publizieren
-> enrollment.marker restriktiv, atomar und gefsynct publizieren
-> vollstaendigen gebundenen Zustand erneut pruefen
```

Ein Fehler vor der Store-Publikation hinterlaesst keinen akzeptierten Store. Ein
Crash nach Store-, aber vor Marker-Publikation ist sichtbar fail-closed und wird
nicht als Erststart behandelt. Gezielt gemeinsames Loeschen von Store und Marker
durch einen lokalen Angreifer bleibt ein Restrisiko; der Marker ist kein
kryptografischer Integritaetsnachweis.

## Passwort pruefen, drosseln und aendern

Passwort-Hashing verwendet ausschliesslich Argon2id als PHC-String mit 64 MiB,
Time Cost 6, Parallelism 1, 16-Byte-Salt, 32-Byte-Hash und
`hash_format_version = 1`. Es gibt keinen Pepper und keinen Fallback. Ein
Rehash erfolgt nur nach erfolgreicher Verifikation und atomar mit dem
Login-Erfolg. Eine normale Passwortaenderung prueft zuerst das aktuelle
Passwort und schreibt den neuen Hash transaktional.

Kalibrierung auf dem aktuellen arm64-Pilot-Mac am 17.07.2026: Je Kandidat wurde
ein Aufwaermhash verworfen und danach acht reale Argon2id-PHC-Hashes bei
unveraendert 65536 KiB Memory, Parallelism 1, 16-Byte-Salt und 32-Byte-Hash
gemessen. Time Cost 4 ergab `146,00 / 145,83 / 149,08 / 145,93 / 150,41 /
148,37 / 145,75 / 145,96 ms` und im Mittel `147,17 ms`. Time Cost 5 ergab
`182,87 / 182,94 / 182,41 / 182,34 / 184,69 / 182,34 / 182,36 / 182,47 ms`
und im Mittel `182,80 ms`. Time Cost 6 ergab `219,66 / 219,18 / 219,30 /
221,22 / 219,21 / 220,08 / 219,71 / 219,85 ms` und im Mittel `219,78 ms`.
Time Cost 6 ist damit die kleinste ganzzahlige Erhoehung, die das Ziel von
ungefaehr 200 bis 350 ms stabil erreicht und auf dem Pilot-Mac deutlich unter
der UX-Obergrenze von 500 ms bleibt. Die Parametererhoehung aendert weder
Argon2id, PHC-Format noch `hash_format_version`. Vorhandene PHC-Hashes mit Time
Cost 3 bleiben pruefbar und werden ausschliesslich nach erfolgreicher
Passwortpruefung per `check_needs_rehash()` atomar aktualisiert.

Passwoerter haben mindestens 15 Unicode-Zeichen und hoechstens 1024 UTF-8-Byte;
mindestens 128 Unicode-Zeichen sind damit zugelassen. Leerzeichen und
Passphrasen sind erlaubt. Es erfolgen weder Trimming, Case-Aenderung,
Unicode-Normalisierung noch Komplexitaets- oder periodische Wechselvorgaben.
Eine kleine lokale Sperrliste wird exakt gegen die unveraenderte Eingabe
geprueft.

Fehlversuche werden vor Rueckgabe transaktional persistiert: 1-4 ohne
Zusatzsperre, danach 30, 60, 120, 240 und ab Versuch 9 hoechstens 300 Sekunden.
Erfolg setzt Zaehler und Sperrzeit zurueck. UTC-Zeitpunkte tragen den Zustand
ueber Neustarts; injizierte monotone Zeit verhindert innerhalb eines Prozesses
eine Verkuerzung. Bei mehr als fuenf Minuten rueckwaerts gesetzter UTC-Uhr gilt
konservativ eine fuenfminuetige Sperre. Recovery besitzt getrennte Zaehler und
Sperrzeitpunkte. Diese Drosselung verhindert keine Offline-Angriffe auf kopierte
Hashes.

## Recovery-Codes erzeugen, verbrauchen und regenerieren

Ein Satz besitzt genau zehn Codes mit 80 Bit Zufall im Format
`JKM1-XXXX-XXXX-XXXX-XXXX-C`. Die kontrollierte ASCII-Normalisierung entfernt
nur Bindestriche und ASCII-Leerzeichen, wandelt ASCII in Grossschrift sowie
`O` zu `0` und `I`/`L` zu `1`; Unicode-Lookalikes werden abgelehnt. Prefix,
Laenge und Crockford-Pruefsymbol muessen stimmen.

Persistiert werden ausschliesslich Code-ID, individueller 16-Byte-Salt,
`SHA-256(salt || canonical_code)`, Formatversion, Satz-ID, Status und technische
Zeitpunkte. Die Pruefung vergleicht konstantzeitnah gegen alle aktiven Codes.
Erfolgreicher Verbrauch und Wechsel zu `password_reset_pending` erfolgen in
einer `BEGIN IMMEDIATE`-Transaktion; konkurrierende Doppelnutzung kann nur
einmal erfolgreich sein.

Regeneration ist zweiphasig: Vorbereitung persistiert einen unbestaetigten Satz,
waehrend der alte aktive Satz gueltig bleibt. Nur die Bestaetigung aktiviert den
neuen Satz und widerruft den alten atomar. Crash oder Abbruch vor Bestaetigung
laesst mindestens den alten bestaetigten Satz gueltig. Klartextcodes werden nur
einmal an den aufrufenden Prozess zurueckgegeben und sind aus dem Store nicht
rekonstruierbar. Es gibt keine Datei-, Zwischenablage-, Log-, Backup- oder
Diagnoseausgabe.

## Security-Dateirechte und Ausschluss

Auf POSIX-Systemen verwendet `security/` Modus `0700`; Datenbank, Marker und
SQLite-Sidecars verwenden `0600`. Setzen und Pruefen sind in Infrastructure
gekapselt und wirken nie ausserhalb des Security-Verzeichnisses. Andere
Plattformen melden POSIX-Schutz als nicht verifizierbar, niemals als bestaetigt.

Alle fachlichen Backup-/Restore-Pfade bleiben Allowlist-basiert: ausschliesslich
`kompetenzmanager.sqlite` und registrierte Managed Files sind Backupinhalt.
Restore ersetzt ausschliesslich fachliche Live-Komponenten. Security Store,
Marker und Sidecars werden nicht gelesen, kopiert, gestaged, ersetzt, geloescht,
exportiert oder an Diagnose/Support angehaengt.

Dieses Dokument beschreibt freigegebene oder geplante Schreibprozesse fuer fachliche Daten.

Kein Schreibprozess darf implementiert werden, bevor sein Lebenszyklus hier dokumentiert ist.

## macOS-Pilotstart und lokale Datenordner

Start: Die installierte `.app` wird fuer einen macOS-Benutzer geoeffnet.

Technischer Pfad:

```text
PySide Entry Point
-> RuntimePaths / sichere Ordnerpruefung
-> vorhandene Benutzerdatenbank oder einmalige Initialisierung
-> bestehende Adapter-/Repository-/SQLite-Initialisierung
```

Die App legt bei Bedarf den Benutzerordner sowie `documents/`, `exports/`, `backups/` und `logs/` an. Eine vorhandene `kompetenzmanager.sqlite` wird nie durch Bundleinhalte ersetzt. Die technische Smoke-Test-Variante `empty` enthaelt keine Startdatenbank und laesst den vorhandenen produktiven Initialisierungspfad eine leere Schuelerdatenbasis mit Stammdaten- und Katalogdefaults anlegen.

Die historische explizite Buildvariante `laura` bleibt ausschließlich als
interner Paket-/Runtime-Testpfad erhalten. Sie ist nicht der Freigabepfad für
die Version-0.2.0-Übergabe. Dort bleiben App und DMG leer; synthetische
Fachdaten gelangen ausschließlich als separates, vollständig verifiziertes
`.jkmbackup` über den normalen Restore-Vertrag in die lokale Runtime. Der
Entwicklerstart bleibt bei `data/kompetenzmanager.sqlite`.

## Technisches macOS-Pilotbackup

Start: Die Lehrkraft hat die App vollstaendig geschlossen und startet bewusst `PILOT_BACKUP.sh`.

Schreibprozess:

```text
Prozesspruefung
-> SQLite Online-Backup der geschlossenen lokalen Datenbank
-> Kopie des verwalteten documents/-Baums
-> neuer backups/YYYYMMDD-HHMMSS/-Ordner
```

Eine vorhandene Sicherung wird nie ueberschrieben. Das Skript aendert weder Benutzerdatenbank noch Dokumente und fuehrt keine Wiederherstellung aus. Eine technische Wiederherstellung bleibt ein separater, manuell gepruefter Eingriff.

## Verifiziertes Anwendungsbackup erstellen und pruefen

### Sichtbarer manueller Ausloeser in Einstellungen

Start: Die Lehrkraft öffnet `Einstellungen > Datensicherung`, wählt bewusst einen Zielordner oder eine bestehende `.jkmbackup`-Datei und erhält nur nach vollständiger Verifikation ein Ergebnis. Die UI speichert weder Zielordner noch eine eigene Historie.

Wiederherstellung: Auswahl -> isolierte Prüfung -> datensparsame Vorschau ->
ausdrückliche Bestätigung -> Prepared-Staging und erneute Prepared-Prüfung ->
Runtime-gebundener Handoff -> authentisierte Worker-Uebernahme. Ein
erfolgreiches `Popen` allein gilt nicht als Workerstart. Der Worker bestaetigt
erst nach Handoff- und Lock-Pruefung persistent `worker_started`, wartet dann
ohne Poll-Sleep auf das vollstaendige Ende der Haupt-App und erstellt
anschliessend das vorhandene verpflichtende Sicherheitsbackup vor dem ersten
Live-Rename. Bei jedem Fehler vor erfolgreicher Worker-Uebernahme bleibt die
App geöffnet und Live-Daten bleiben unverändert. Es gibt keine automatische
Sicherung, Erinnerung oder Aufbewahrungsautomatik.

Qt-Ausfuehrung ab Sprint 0.2A.4a: Backup-Erstellung, Backup-Pruefung, Restore-Pruefung, Prepared-Staging und Prepared-Pruefung laufen als jeweils genau ein unveraenderlicher Auftrag ueber den shell-eigenen Operations-Controller in einem `QThread`. Der `QObject`-Worker ruft ausschliesslich die vorhandenen Application-Services auf und emittiert technische Ergebnisse, Fehlerklassen und neutrale Phasen. UI-Projektion, Dateidialoge, Vorschau, Bestaetigung, Handoff, Prozessstart und App-Beendigung bleiben im Qt-Hauptthread. Ohne sicheren Core-Cancel-Vertrag gibt es keinen Abbruch; Close und Navigation werden bis zum echten Thread-Ende kontrolliert blockiert. `terminate()` ist ausgeschlossen.

Start: Ein expliziter Application-Command erhaelt Datenbankpfad, vollstaendige `RuntimePaths`, Zielordner, Buildinformationen und UTC-Zeitquelle. In Sprint 0.2A.2 existiert dafuer noch keine sichtbare UI und kein automatischer Ausloeser.

Technischer Prozess:

```text
CreateBackupCommand
-> BackupApplicationService
-> BackupService
-> SQLiteBackupEngine / sqlite3.Connection.backup()
-> Snapshot integrity_check + foreign_key_check
-> BackupInventoryService liest ausschliesslich den Snapshot
-> verwaltete Dateien stabil kopieren und SHA-256 bilden
-> kanonisches Manifest v1 und ZIP-Stagingdatei schreiben
-> BackupVerifier prueft das geschlossene Archiv isoliert erneut
-> flush / fsync / atomare exklusive Veroeffentlichung
```

Der Prozess liest die Live-Datenbank kontrolliert und schreibt niemals in sie. Er kopiert keine laufende SQLite-Datei, keine `-wal`- oder `-shm`-Datei und verwendet keinen externen SQLite-Prozess. Bei einer laenger blockierten Transaktion endet das begrenzte Warten mit `BackupBusyError`.

Das Inventar stammt aus dem Snapshot. Registrierte Dokumente innerhalb `RuntimePaths.documents` werden aktiv wie soft-deaktiviert aufgenommen. Finale Bericht- und LEG-PDF-Artefakte werden aufgenommen und ihre gespeicherten Groessen und SHA-256-Hashes gegen die tatsaechlichen Dateien geprueft. Fehlende, veraenderte, verlinkte oder besondere verwaltete Dateien, unbekannte Nutzdateien unter `documents/` sowie Hashabweichungen brechen den gesamten Prozess ab. Externe Dokumentreferenzen werden nur gezaehlt und nie kopiert.

Verwaltete Dateien werden relativ zu einem geoeffneten `documents`-Directory-FD gelesen. Jede Pfadkomponente wird ohne Symlink-Folgen geoeffnet; Geraet, Inode, Dateityp, Groesse und Aenderungszeit muessen vom Inventar bis nach dem Streaming identisch bleiben. Ein Parent-Verzeichnis-Austausch oder ein Endkomponenten-Symlink kann dadurch keine externe Datei in das Backup umlenken.

Bei jedem Fehler werden temporaeres Archiv und Staging entfernt; vorhandene Backups bleiben unveraendert und es entsteht kein Erfolgsergebnis. Bei der exklusiven Veroeffentlichung darf der finale Pfad nur entfernt werden, wenn genau dieser Aufruf den Hardlink zuvor selbst erfolgreich erzeugt hat. Der abschliessende Verifier prueft ZIP-Struktur und CRC, Pfadsicherheit und macOS-Namenskollisionen, Limits vor und waehrend der Extraktion, Manifestversion, Datenbank- und Dateihashes, SQLite-Integritaet, Fremdschluessel, Schema-Fingerprint, Counts und vollstaendiges Inventar in einem isolierten temporaeren Verzeichnis.

Der Packaged-App-Smoke validiert vor `prepare_runtime_storage()` einen expliziten Smoke-Marker und eine eigene temporaere Datenwurzel. Fehlt eine der beiden unabhaengigen Bedingungen, endet der Start ohne Anlegen von Runtime-Verzeichnissen, Datenbank, PDF oder Backup.

Dieser Lifecycle veraendert keine fachlichen Daten. Restore, Vorschau, Migration, automatische Sicherung, Aufbewahrung, Verschluesselung, Signierung, Passwortschutz, Nutzerkonto, Import, Onboarding und Cloud sind nicht freigegeben.

## Datenbankschema V1 initialisieren und Kompatibilitaet pruefen

Start: Die bestehende SQLite-Initialisierung oeffnet eine neue oder vorhandene lokale Datenbank.

Technischer Prozess fuer eine schemafreie Datenbank:

```text
SQLiteDatabase.initialize_schema()
-> vor Schemaerzeugung keine nicht-internen Schemaobjekte festgestellt
-> BEGIN IMMEDIATE
-> vollstaendiges V1-Schema erzeugen
-> PRAGMA user_version = 1
-> COMMIT
```

Eine vorhandene Datenbank mit nicht-internen Schemaobjekten und `user_version = 0` bleibt beim normalen Start unversioniert. Sie wird weder als V1 adoptiert noch in-place migriert. Der bestehende fachliche Betrieb bleibt davon getrennt. `DatabaseCompatibilityInspector` liest Version und vollstaendigen Schemafingerprint ausschliesslich read-only; `DatabaseCompatibilityPolicy` klassifiziert exaktes V1 als `EXACT`, den registrierten unversionierten `c029aff`-Vorgaenger als `MIGRATION_REQUIRED` und unbekannte oder neuere Staende als `INCOMPATIBLE`.

## Restore-Backup technisch verifizieren und Vorschau erzeugen

Start: Eine explizite `VerifyRestoreBackupQuery` uebergibt den Pfad eines bestehenden `.jkmbackup`. Es gibt keinen sichtbaren UI-Ausloeser.

```text
VerifyRestoreBackupQuery
-> RestoreApplicationService
-> RestoreVerifier
-> BackupVerifier
-> Archivgroesse und SHA-256 erneut binden
-> sichere isolierte temporaere Extraktion
-> Datenbank read-only oeffnen
-> Manifest- und Datenbankversion vergleichen
-> vollstaendigen Kompatibilitaetsfingerprint und Status bestimmen
-> integrity_check / foreign_key_check
-> Counts und Managed Files pruefen
-> datensparsame RestorePreview erzeugen
-> temporaeres Verzeichnis vollstaendig entfernen
```

Der Prozess veraendert weder die Kandidatendatenbank noch Live-Daten oder Managed Files und fuehrt keine Migration aus. Ein Widerspruch zwischen Manifest und tatsaechlicher Datenbankversion, ein unbekannter Fingerprint, eine neuere Datenbank, Integritaets- oder Fremdschluesselfehler, falsche Counts oder fehlende beziehungsweise veraenderte Managed Files fuehren zu einem typisierten Fehler ohne Ergebnis. Es bleiben keine Stagingdaten zurueck.

Nicht Bestandteil dieses read-only Verifikations-Lifecycles sind persistentes Restore-Staging, Pfad-Rebasing und Sicherheitsbackup; diese werden im nachfolgenden Sprint-0.2A.3b-Lifecycle getrennt freigegeben. Worker, Austausch, Rollback, Journal, Start-Recovery, Neustart und UI bleiben weiterhin ausgeschlossen.

## Restore-Staging vorbereiten, pruefen und bereinigen

Start: Ein expliziter Application-Command uebergibt ein zuvor pruefbares `.jkmbackup`, die aktuelle `RuntimePaths`-Projektion und optional eine technische Restore-ID. Es gibt keinen sichtbaren UI-Ausloeser.

```text
PrepareRestoreStagingCommand
-> BackupVerifier und RestoreVerifier vollstaendig ausfuehren
-> Archivgroesse und SHA-256 an einen geoeffneten Dateideskriptor binden
-> restore-staging/<restore-id>/ exklusiv anlegen
-> dieselben gebundenen Archivbytes sicher nach source/ extrahieren
-> Datenbank nach prepared/ kopieren
-> exaktes V1 unveraendert uebernehmen oder registriertes V0 transaktional auf V1 migrieren
-> Managed Files anhand technischer Manifest-IDs nach prepared/documents/ materialisieren
-> Managed documents.file_path in eigener Transaktion rebasen
-> Prepared-Staging vollstaendig erneut pruefen
-> staging-state.json auf completed setzen
```

Restore-Staging schreibt niemals in die produktive Datenbank oder in produktive `documents/`. Migrationen laufen ausschliesslich auf der Staging-Kopie. Unterstuetzt werden nur exaktes V1 und der registrierte V0-Vorgaenger; unbekannte, widerspruechliche oder neuere Schemata werden abgelehnt. Bei V0 wird der vollstaendige Fingerprint vor der Transaktion bestaetigt, kein fachlicher Wert oder keine ID veraendert und `PRAGMA user_version = 1` als letzter Schritt gesetzt. Jeder Fehler rollt die laufende Staging-Transaktion zurueck und markiert den eindeutig zugeordneten Staging-State technisch als `failed`.

Managed Files werden ausschliesslich aus dem verifizierten Manifest gelesen. Symlinks, Sonderdateien, Traversal, fehlende Dateien und Hash- oder Groessenabweichungen blockieren. Regulare Dokumente erhalten einen technischen Zielpfad; Bericht- und LEG-PDFs werden an ihren bereits registrierten relativen Artefaktpfaden materialisiert. Externe Referenzen, PDF-Pfade, Snapshot-JSON, Snapshot-Hashes und alle fachlichen IDs bleiben unveraendert. Nach Migration, Materialisierung und Rebase werden Integritaet, Fremdschluessel, V1-Fingerprint, Counts, Tabelleninhalte, Managed-File-Inventar sowie PDF-Bytes und -Hashes erneut geprueft.

`VerifyPreparedRestoreQuery` ist wiederholbar und liest ausschliesslich ein eindeutig zugeordnetes abgeschlossenes Staging. Unbekannte oder widerspruechliche Phasen werden nicht automatisch fortgesetzt. `CleanupRestoreStagingCommand` darf nur das direkte, per gueltiger Restore-ID und passendem State gebundene Kind von `restore-staging/` entfernen; beliebige Pfade werden nie akzeptiert. Erfolg und kontrollierter Fehler koennen so gezielt bereinigt werden.

## Restore-Sicherheitsbackup erzeugen

Start: Ein expliziter, vom Staging getrennter Application-Command fordert fuer eine technische Restore-ID das Sicherheitsbackup des aktuellen Live-Bestands an.

```text
CreateRestoreSafetyBackupCommand
-> RestoreSafetyBackupService
-> vorhandener BackupService
-> backups/restore-safety/<restore-id>/
-> vorhandener BackupVerifier
-> technisches Ergebnis mit Pfad, Groesse und SHA-256
```

Das Zielverzeichnis und vorhandene Backups werden nie ueberschrieben. Ein Fehler erzeugt keine Restore-Freigabe. Sicherheitsbackup, Restore-Staging, produktive SQLite-Datei und produktive `documents/` sind disjunkt. Dieser Sprint verbindet das Sicherheitsbackup noch nicht mit einem produktiven Austausch.

Nicht Bestandteil beider Lifecycles sind Live-Austausch, Rename der produktiven Datenbank oder `documents/`, Worker, Instanz-Lock, Wartungszustand, Live-Rollback, Live-Journal, Start-Recovery, App-Neustart oder UI.

## Produktiven Restore ausfuehren und journalgestuetzt absichern

Start: Eine kontrollierte Application-Funktion erzeugt nach vollstaendiger Prepared-Pruefung eine einmalige Handoff-Datei. Der normale App-Prozess beendet alle Datenbankzugriffe und uebergibt den gehaltenen Runtime-Lock kontrolliert an den Qt-freien Worker. Es gibt keine sichtbare UI und keine frei waehlbaren Zielpfade.

```text
CreateRestoreHandoffCommand
-> Handoff 0600 atomar schreiben
-> Handoff atomar nach consumed umbenennen
-> Runtime-Lock im Worker validieren und worker_started journalen
-> Workerstart ueber privaten Ready-Kanal bestaetigen
-> Haupt-App kontrolliert vollstaendig beenden
-> Worker wartet bis zum EOF des Parent-Lebensdauerkanals
-> Archiv-, Staging- und Prepared-Bindung erneut pruefen
-> Sicherheitsbackup erstellen und verifizieren
-> Live-DB integrity_check / foreign_key_check / WAL checkpoint
-> Rename-Intent journalen und fsyncen
-> DB, WAL, SHM und documents in rollback/ verschieben
-> Prepared-DB und Prepared-documents nach Live verschieben
-> neuen Live-Bestand read-only vollstaendig pruefen
-> installed_verified
-> App mit einmaligem Resume-Token starten
-> Startup-Handshake abwarten
-> completed
```

Kann Executable, Berechtigung, Argumentliste, Arbeitsverzeichnis,
Lock-Uebergabe oder Ready-Bestaetigung nicht nachgewiesen werden, wird der
Worker beendet und geerntet, der Zustand ohne Live-Mutation auf
`aborted_before_replacement` gesetzt und die Haupt-App bleibt mit einer
datensparsamen Fehlermeldung benutzbar. Der Parent-Lebensdauerkanal verhindert,
dass der Worker vor dem vollstaendigen Prozessende der Haupt-App mit
Preflight oder Austausch beginnt.

Bis einschliesslich `preflight_verified` und vor dem ersten Rename bleiben produktive Bytes unveraendert. Der Austausch besteht ausschliesslich aus atomaren Einzel-Renames auf demselben Dateisystem; die Gesamtoperation ist nur durch Journal und Rollback abgesichert. Ein fehlender oder leerer alter `documents/`-Baum sowie vorhandene oder fehlende `-wal`-/`-shm`-Dateien werden als eigene Zustaende erfasst.

Bei jedem Fehler vor erfolgreichem Startup-Handshake wird der neue Bestand nach `failed-new/` verschoben und der alte DB-, WAL-, SHM- und Documents-Zustand exakt aus `rollback/` wiederhergestellt. Erst nach read-only Integritaets-, Fremdschluessel- und Inventarpruefung darf die alte App neu starten. Scheitert ein Teilrollback oder widersprechen Journal, Pfade, Groessen oder Hashes einander, wird `manual_recovery_required` geschrieben; es startet keine App und nichts wird automatisch bereinigt.

## Unterbrochenen Restore vor App-Start recovern

Start: Jeder normale Start prueft den kanonischen Runtime-Root vor `prepare_runtime_storage()`, Logging, `QApplication`, Datenbankinitialisierung und Pilotdateninstallation.

- Ohne aktives kritisches Journal startet die App normal.
- Vor dem Austausch darf ein Restore kontrolliert abgebrochen werden; Live-Daten bleiben unveraendert.
- Nach begonnenem, aber nicht verifiziertem Austausch hat automatischer Rollback Vorrang.
- `installed_verified` ohne Handshake darf nur begrenzt mit demselben Restore-Vertrag resumed werden; danach erfolgt Rollback.
- Widerspruechliche Existenz-, Groessen- oder Hashbeweise fuehren zu `manual_recovery_required`.
- Recovery ist wiederholbar; abgeschlossene, sauber gerollte oder manuell gesperrte Zustaende werden nicht nochmals mutiert.

Der Startup-Handshake konsumiert einen kurzlebigen Resume-Token atomar, prueft Restore-ID und Token, Live-V1-Kompatibilitaet, SQLite-Integritaet, Fremdschluessel und das erwartete Documents-Inventar und markiert erst danach `completed`. Fachliche Daten werden nicht transformiert; alte Pilot-V0-Daten wurden bereits ausschliesslich im Prepared-Staging migriert.

## Dokumentationsrelevante Faecher speichern

Start: Laura legt in den Einstellungen fest, welche Faecher fuer spaetere Dokumentations- und Auswertungslogik zaehlen sollen.

Schreibprozess: Dokumentationskonfiguration ueber Settings-UI, Desktop Adapter und SQLite-Repository. Ab Sprint 2C wird die Auswahl lesend in Dokumentationsauswertungen angewendet.

Freigegebener PySide-Pfad:

```text
PySide6 SettingsScreen
-> StudentDesktopAdapter
-> SQLiteDocumentationSubjectSettingsRepository
-> SQLite documentation_subject_settings
```

Betroffene Datenquellen:

- `documentation_subject_settings` in SQLite als Source of Truth fuer die Auswahl dokumentationsrelevanter Faecher
- `competencies` nur lesend fuer das Default-Verhalten und die vorhandenen Fachschluessel

Erforderliche IDs:

- bestehender `subject_id`

Automatisch profitierende Ansichten:

- Schuelerlisten-Dokumentationsstatus
- Schuelerprofil-Dokumentationsstand
- offene Kompetenzen / Beobachtungsanlaesse
- Beobachtungshinweise im Halbjahresblick
- Berichtsvorbereitung, falls sie Dokumentationsstatus oder offene Kompetenzen nutzt

Regel: Die Speicherung ersetzt die vollstaendige Auswahl in `documentation_subject_settings`. Wenn keine Settings-Zeilen vorhanden sind, bleibt das bisherige Verhalten erhalten: alle aktiven Katalogfaecher aus `competencies.active = 1` gelten als dokumentationsrelevant. Die Einstellung loescht keine Beobachtungen, veraendert keine Kompetenzdefinitionen und nutzt `competencies.active` nicht als Einstellungsfeld. Nicht dokumentationsrelevante Faecher bleiben in Beobachtungslisten, Kompetenzhistorien und bestaetigten Kompetenzstaenden sichtbar, zaehlen aber nicht als offen im Dokumentationsstand oder in offenen Beobachtungsanlaessen.

## Stundenplaneintrag pflegen

Start: Laura legt in den Einstellungen einen Stundenplaneintrag an, bearbeitet, aktiviert, deaktiviert oder loescht ihn.

Freigegebener PySide-Pfad:

```text
PySide6 SettingsScreen / TimetableEntryDialog
-> TimetableDesktopAdapter
-> TimetableApplicationService
-> TimetableService / TimetableValidator
-> SQLiteTimetableRepository
-> SQLite timetable_entries
```

Betroffene Datenquellen:

- SQLite `timetable_entries` schreibend
- SQLite `competencies` lesend zur Aufloesung und Validierung vorhandener `subject_id`
- SQLite `groups`, `courses` und `course_groups` lesend zur zielartgerechten Validierung von `target_id`

Erforderliche IDs:

- neue oder bestehende `timetable_entry_id`
- bestehende `subject_id`
- bestehende, zu `target_type` passende `target_id`

Regel: Anlegen und Aendern validieren Zeitbereich, Referenzen und aktive Ueberschneidungen vor dem Schreiben. Aktivieren durchlaeuft dieselben Regeln. Loeschen markiert nur den ausdruecklich gewaehlten Stundenplaneintrag mit `deleted_at` und deaktiviert ihn; bestehende Stammdaten und Stundenplan-IDs bleiben unveraendert und geloeschte IDs werden nicht wiederverwendet. Die Leseprojektion speichert nichts und berechnet aktuelle, naechste und heutige Stunden ausschliesslich aus aktiven, nicht geloeschten Eintraegen und einem explizit uebergebenen Zeitpunkt.

## Schueler anlegen

Start: Lehrkraft oder Verwaltung legt einen neuen Schueler an.

Schreibprozess: atomare V3-Schueleranlage mit initialer Einschreibung.

Primaerer UI-Einstieg: PySide-Dialog `Neuer Schüler`.

Lokal implementierter PySide-Pfad:

```text
PySide6 GUI
-> StudentDesktopAdapter.save_new_student
-> CreateStudentWithInitialEnrollment
-> V3StudentRepository + StudentSchoolYearAssignmentRepository
-> SQLite students + student_school_year_assignments
```

Betroffene Datenquellen:

- V3-`students` fuer Stammdaten
- eindeutiges aktuelles `school_years`
- `student_school_year_assignments` fuer die initiale Einschreibung

Erforderliche IDs:

- neuer `student_id`
- vorhandene `school_year_id`
- bestehender `group_id`
- bestehender `course_id`

Regel: Stammdaten und initiales `enrolled`-Assignment committen gemeinsam
oder gar nicht. Das aktuelle Schuljahr wird zentral aufgeloest und nicht
implizit aus Systemdatum oder Seedwert angenommen. Der V3-Schuelerdatensatz
enthaelt keine Membershipfelder. Synthetische Schüler entstehen nur in
expliziten neuen Final-V3-Testdatenbanken; vorhandene lokale Daten werden
nicht ersetzt.

## Dokument oder Medium hinzufuegen

Start: Lehrkraft fuegt im Schuelerprofil oder Beobachtungsdialog eine Datei hinzu oder entfernt eine Datei aus dem Schuelerprofil.

Schreibprozess: Dokumenten- und Medien-MVP ueber PySide.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> StudentDesktopAdapter
-> Dateiablage data/documents/<student_id>/
-> SQLiteDocumentRepository
-> SQLite documents
```

Betroffene Datenquellen:

- SQLite `documents` als fachliche Source of Truth fuer Metadaten
- Dateisystem `data/documents/<student_id>/` fuer physische Dateien
- optional `observations`, wenn die Datei als Beobachtungsanhang verknuepft wird

Erforderliche IDs:

- bestehender `student_id`
- optional bestehender `observation_id`
- neuer `document_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Beobachtungsdetails
- spaeter Berichte und Exporte

Regel: SQLite speichert nur Metadaten und keine Datei-BLOBs. Die Datei wird in den App-Datenordner kopiert und studentenzentriert abgelegt. Ein Beobachtungsanhang gehoert weiterhin zum Schueler und traegt nur zusaetzlich den optionalen Beobachtungsbezug. Entfernen ist ein Soft Delete ueber `documents.active = 0`; die physische Datei wird in diesem MVP nicht automatisch geloescht.

## Schueler archivieren

Start: Schueler soll nicht mehr aktiv in Ansichten erscheinen.

Schreibprozess: `StudentDesktopAdapter.archive_student_master_data` über
`ArchiveStudent`.

Betroffene Datenquellen:

- V3-`students`
- `student_school_year_assignments` ausschließlich zur fail-closed Prüfung

Erforderliche IDs:

- `student_id`
- expliziter `as_of`-Tag

Regel: Archivierung ändert kein Assignment und erzeugt kein `exited`.
Bei aktueller Einschreibung wird sie blockiert. Historische Daten und
Beobachtungen bleiben über `student_id` gültig.

## Schueler aendern

Start: Stammdaten eines bestehenden Schuelers werden korrigiert.

Schreibprozess: `StudentDesktopAdapter.save_existing_student` über
`UpdateStudentMasterData`.

Betroffene Datenquellen:

- V3-`students`

Erforderliche IDs:

- bestehender `student_id`

Regel: Dieser Pfad ändert ausschließlich Vorname, Nachname und Notiz.
Zuordnungen werden nur über den getrennten datierten Einzelwechsel geändert.
`student_id` und sämtliche Assignments bleiben erhalten.

## Stammgruppe anlegen

Start: Neue organisatorische Stammgruppe wird benoetigt.

Schreibprozess: Stammgruppenverwaltung ueber PySide-Stammdaten.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> MasterDataDesktopAdapter
-> SQLiteMasterDataRepository
-> SQLite groups
```

Betroffene Datenquellen:

- `groups` in SQLite als fachliche Source of Truth
- `data_groups` als historische Excel-/Exportprojektion

Erforderliche IDs:

- neuer `group_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Schuelerverwaltung

Regel: Schueler werden einer Stammgruppe ausschließlich durch ein datiertes
`student_school_year_assignments.group_id` zugeordnet. Das Anlegen einer
Stammgruppe erzeugt oder verändert kein Assignment. Eine
Kursverbundzuordnung ist eine getrennte Stammdatendefinition und keine
Schülermitgliedschaft.

## Stammgruppe aendern

Start: Name oder Status einer bestehenden Stammgruppe wird angepasst.

Schreibprozess: Stammgruppenverwaltung ueber PySide-Stammdaten.

Betroffene Datenquellen:

- `groups` in SQLite als fachliche Source of Truth
- `data_groups` als historische Excel-/Exportprojektion

Erforderliche IDs:

- bestehender `group_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `group_id` bleibt erhalten. Umbenennen schreibt nur den Namen und
loest keine Schueler-Umbuchung aus. Deaktivierung benötigt einen expliziten
Stichtag und wird blockiert, solange aktuelle oder zukünftige
`enrolled`-Assignments die Gruppe referenzieren. Historische Referenzen
bleiben lesbar.

## Kurs anlegen

Start: Neuer Kurs/Jahrgang wird benoetigt.

Schreibprozess: Kursverwaltung ueber PySide-Stammdaten.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> MasterDataDesktopAdapter
-> SQLiteMasterDataRepository
-> SQLite courses
```

Betroffene Datenquellen:

- `courses` in SQLite als fachliche Source of Truth
- `data_courses` als historische Excel-/Exportprojektion

Erforderliche IDs:

- neuer `course_id`
- bewusst gewählte `year_level` 1, 2 oder 3

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `year_level` wird nicht aus Name, Farbe, Sortierung oder Listenposition
abgeleitet; mehrere Kurse derselben Stufe sind zulässig. Kursfarbe wird mit
Name und Hex-Wert am Kurs gespeichert und nicht an einzelnen Schuelern. Neue
Kurse werden dem Default-Kursverbund hinzugefuegt, damit sie in der
kursverbundbezogenen Uebersicht sichtbar bleiben.

## Kurs aendern

Start: Name, Farbe oder Status eines bestehenden Kurses wird angepasst.

Schreibprozess: Kursverwaltung ueber PySide-Stammdaten.

Betroffene Datenquellen:

- `courses` in SQLite als fachliche Source of Truth
- `data_courses` als historische Excel-/Exportprojektion

Erforderliche IDs:

- bestehender `course_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Berichte

Regel: `course_id` bleibt erhalten; `year_level` muss weiterhin 1, 2 oder 3
sein. Deaktivierung benötigt einen expliziten Stichtag und wird bei aktuellen
oder zukünftigen `enrolled`-Assignments blockiert. Historische Assignments
bleiben unverändert und lesbar. Schuelerkartenfarbe aktualisiert sich aus
`course_id` und `courses.color_hex`.

## Kursverbund anlegen oder aendern

Start: Ein kursverbundbezogener Mathe-/Deutsch-Scope wird angelegt oder bearbeitet.

Schreibprozess: Kursverbundverwaltung ueber PySide-Stammdaten.

Freigegebener PySide-Pfad:

```text
PySide6 GUI
-> MasterDataDesktopAdapter
-> SQLiteMasterDataRepository
-> SQLite course_groups
-> SQLite course_group_student_groups
-> SQLite course_group_courses
```

Betroffene Datenquellen:

- `course_groups`
- `course_group_student_groups`
- `course_group_courses`

Erforderliche IDs:

- bestehender oder neuer `course_group_id`
- mindestens ein bestehender `group_id`
- mindestens ein bestehender `course_id`

Automatisch profitierende Ansichten:

- PySide-Uebersicht `Stammgruppen und Schülerbestand`
- Schuelerliste mit Kursverbund-/Kursfilter
- Stammdaten-Seite

Regel: Name, Stammgruppen- und Kurszuordnung werden atomar gespeichert. Neue Kursverbuende erhalten eine stabile `course_group_id`. Doppelte Kursverbundnamen werden vor dem Speichern abgefangen. Die Relationstabellen werden beim Speichern vollstaendig fuer den Kursverbund ersetzt. Es werden keine Schueler umgebucht und keine Beobachtungsdaten veraendert.

## Stammdaten-Defaults initialisieren

Start: SQLite-Datenbank wird ohne vorhandene Stammgruppen oder Kurse geoeffnet.

Schreibprozess: Initialisierung ueber `SQLiteDatabase.ensure_master_data_defaults()`.

Betroffene Datenquellen:

- `groups`
- `courses`
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`

Regel: Defaults fuer Stammgruppen, Kurse und `Mathe/Deutsch Kursverbund A` werden nur erzeugt, wenn der jeweilige Stammdaten-Scope leer ist. Bestehende produktive Stammdaten werden nicht ueberschrieben.

## Beobachtung erfassen

Start: Lehrkraft dokumentiert eine Beobachtung zu einem Schueler.

Schreibprozess: PySide-Beobachtungsdialog ueber `StudentDesktopAdapter`, `observation.create`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`
- SQLite `documentation_subject_settings` nur lesend fuer die Fachauswahl
- Export-/Legacy-Projektionen `data_observations` und `data_observation_competencies`
- spaeter optional `data_media`

Erforderliche IDs:

- neuer `observation_id`
- bestehender `student_id`
- bestehender oder aus dem v1-Katalog abgeleiteter `competency_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzansicht
- Berichte
- Dashboards

Regel: Beobachtung ist Source of Truth. Auswertungen leiten sich daraus ab. Die Schnellauswahl im Beobachtungsdialog ist eine nicht schreibende Adapterprojektion aus bereits aktiven Beobachtungen und ihren Kompetenzbewertungen: nur aktive `current`-Kompetenzen, je Schueler und Fach maximal vier eindeutige Eintraege, neueste zuerst. Sie erzeugt keine Tabelle, keine Historie und keine zusaetzliche Persistenz und wird nach erfolgreichem Speichern neu abgeleitet.
Neue Beobachtungen koennen nur mit dokumentationsrelevanten aktiven Faechern aus der aktuellen Settings-Auswahl angelegt werden; ohne Settings-Zeilen gilt der aktive Katalog. Die Kompetenzauswahl bietet dabei ausschliesslich aktive `current`-Kompetenzen an. Beobachtung und Kompetenzbewertungen werden atomar gespeichert; eine Bewertung gehoert zur konkreten Kompetenz, nicht global zur Beobachtung. Die sichtbare Struktur lautet Fach -> Kompetenzbereich -> Thema -> Kompetenz und wird ueber vorhandene Felder abgebildet: `subject_id` / `subject_name`, `learning_area`, `competency_group`, `description` / `competency_text`. `offen` ist kein gespeicherter Ratingwert; eine nicht bewertete Kompetenz erzeugt keine Zeile in `observation_competency_ratings`. Eine bewusst aktivierte Schnellbeobachtung darf ohne Kompetenzbewertungen gespeichert werden, wenn `note` nach dem Trimmen nicht leer ist. Sie erzeugt keine Zeile in `observation_competency_ratings` und wirkt deshalb nicht auf kompetenzbezogene Projektionen. Medien/Anhaenge und Berichte bleiben im bestehenden separaten Prozess.

## Beobachtung aendern

Start: Lehrkraft korrigiert eine bestehende Beobachtung im Schuelerprofil.

Schreibprozess: PySide-Schuelerprofil oeffnet den Beobachtungsdialog mit `observation_id`; Speichern laeuft ueber `StudentDesktopAdapter`, `observation.update`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`
- SQLite `documentation_subject_settings` nur lesend fuer die Fachauswahl
- Export-/Legacy-Projektionen `data_observations` und `data_observation_competencies`

Erforderliche IDs:

- bestehender `observation_id`
- bestehender `student_id`
- bestehende `competency_id` je Bewertung

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzuebersicht
- Kompetenzansicht
- Berichte

Regel: `observation_id` bleibt erhalten. Beobachtungsfelder werden aktualisiert; Kompetenzbewertungen werden fuer die Beobachtung atomar ersetzt. Die Fachanzeige wird weiter aus den Kompetenzfaechern abgeleitet. Wenn das gespeicherte Fach inzwischen nicht dokumentationsrelevant ist, bleibt es beim Bearbeiten sichtbar und wird nicht automatisch ersetzt oder entfernt. Bereits bewertete `legacy`- oder inaktive Kompetenzen bleiben mit ihrer gespeicherten `competency_id`, Hierarchie, ihrem Text und Rating sichtbar, bewertbar und entfernbar; es erfolgt keine Ersetzung oder Migration. Eine Bewertung wird nur gespeichert, wenn eine konkrete Kompetenz in dieser Beobachtung bewertet wird; `offen` wird nicht als eigener Ratingwert gespeichert. Eine gespeicherte Schnellbeobachtung wird beim Bearbeiten aus nichtleerer Notiz und fehlenden Kompetenzbewertungen erkannt. Kompetenzen koennen spaeter ergaenzt werden; dann wird der Schnellbeobachtungsmodus beendet und die normale Bewertungsvalidierung gilt. Werden alle Kompetenzen einer normalen Beobachtung entfernt, ist Speichern nur nach bewusster Aktivierung des Schnellbeobachtungsmodus und mit nichtleerer Notiz erlaubt.

## Beobachtung loeschen

Start: Lehrkraft blendet eine fehlerhafte Beobachtung aus dem Schuelerprofil aus.

Schreibprozess: PySide-Schuelerprofil sendet `observation_id`; Loeschen laeuft ueber `StudentDesktopAdapter`, `observation.delete`, `ObservationService`, `SQLiteObservationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `observations`
- SQLite `observation_competency_ratings`

Erforderliche IDs:

- bestehender `observation_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzuebersicht
- Kompetenzansicht
- Berichte

Regel: Loeschen ist ein Soft Delete und setzt `observations.active = 0`. Rating-Zuordnungen bleiben historisch erhalten, aktive Profil- und Kompetenzuebersichten lesen nur aktive Beobachtungen.

## Kompetenzstand bestaetigen

Start: Lehrkraft uebernimmt oder aendert im Schuelerprofil den berechneten Kompetenzstand-Vorschlag.

Schreibprozess: PySide-Schuelerprofil sendet `student_id`, `competency_id` und `confirmed_rating`; Speichern laeuft ueber `StudentDesktopAdapter`, `SQLiteStudentCompetencyConfirmationRepository` und SQLite.

Betroffene Datenquellen:

- SQLite `student_competency_confirmations`

Erforderliche IDs:

- bestehender `student_id`
- bestehender `competency_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Kompetenzuebersicht
- Berichtsvorschau

Regel: Der bestaetigte Kompetenzstand ist eine paedagogische Entscheidung der Lehrkraft. Er ueberschreibt keine Beobachtungen und veraendert den berechneten Vorschlag nicht. Neue Beobachtungen aktualisieren den Vorschlag, aber nicht automatisch den bestaetigten Stand.

## Kompetenz ergaenzen

Start: Fachliche Kompetenzstruktur wird erweitert.

Schreibprozess: Fachliche Konfiguration, spaeter freizugeben.

Betroffene Datenquellen:

- `data_competencies`
- optional `data_subjects`

Erforderliche IDs:

- neuer `competency_id`
- bestehender oder neuer `subject_id`
- optional `parent_competency_id`

Automatisch profitierende Ansichten:

- Beobachtungsdialog
- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Regel: Kompetenzstruktur wird nicht aus Beobachtungstexten abgeleitet. Sprint 3A fuehrt keine neuen DB-Felder wie `competency_area` oder `topic` ein. Die vorhandenen Felder werden fachlich gemappt: Fach = `subject_id` / `subject_name`, Kompetenzbereich = `learning_area`, Thema = `competency_group`, konkrete Kompetenz = `description` / `competency_text`, Kurzlabel = `label`. Sprint 3B ergaenzt konkrete Arbeitskatalog-Kompetenzen ueber neue stabile `competency_id`s und nutzt die optionale CSV-Spalte `competency_label` zur Befuellung des bestehenden SQLite-Feldes `label`.

## Kompetenzkatalog importieren oder aktualisieren

Start: PySide-App oeffnet eine SQLite-Datenbank ohne vorhandene Kompetenzen oder mit einem aelteren lokalen Kompetenzkatalog.

Schreibprozess: Idempotenter Katalogimport ueber `StudentDesktopAdapter`, `CurriculumDesktopAdapter` und `SQLiteCompetencyRepository.ensure_catalog_defaults()`.

Freigegebener PySide-/SQLite-Pfad:

```text
data/curriculum_catalog_v1.csv
-> CurriculumDesktopAdapter
-> SQLiteCompetencyRepository
-> SQLite competencies
```

Betroffene Datenquellen:

- `data/curriculum_catalog_v1.csv` als Seed-Quelle
- SQLite `competencies`
- Export-/Legacy-Projektion `data_competencies`

Erforderliche IDs:

- bestehende `competency_id` aus dem Katalog
- bestehende `subject_id` / `subject_key` aus dem Katalog

Automatisch profitierende Ansichten:

- Beobachtungsdialog
- Schuelerprofil
- Kompetenzansicht
- Dokumentationsstand
- Berichte und Dashboard, sobald sie die neuen Katalogmetadaten nutzen

Regel: Der Import ist ab Sprint 3B ein idempotenter Upsert. Bei leerer Tabelle wird der vollstaendige CSV-Katalog importiert. Bei bestehenden lokalen Datenbanken werden neue CSV-IDs eingefuegt und vorhandene CSV-IDs aktualisiert, ohne lokale Nicht-CSV-Kompetenzen zu loeschen. Sprint 4A aktualisiert dabei auch `grade_band`, `learning_stage`, `catalog_status`, `catalog_default_active` und `activation_group_key`. `competencies.active` vorhandener IDs wird nicht aus dem CSV ueberschrieben, damit alte grobe oder lokal deaktivierte Kompetenzen nicht ungefragt reaktiviert oder deaktiviert werden. `catalog_default_active` speichert nur den Katalogstandard. Kompetenzstaende werden weiterhin aus Beobachtungen abgeleitet und nicht manuell doppelt gespeichert. Alte grobe Kompetenzen bleiben historisch lesbar und bestehende `observation_competency_ratings` werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Fehlen Sprint-4A-Spalten in alten CSV-Dateien, setzt der Parser sichere Defaults: `learning_stage = cross_stage`, `catalog_status = current`, `activation_group_key = ''` und `catalog_default_active` aus dem alten `is_active`. Die Sprint-4-Lehrplanuebernahmen fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz sind abgeschlossen; Religion blieb ausserhalb dieses Katalogabgleichs.

## Kompetenzkatalog qualitaetssichern

Start: Vor einer fachlichen Ueberarbeitung von `data/curriculum_catalog_v1.csv`.

Schreibprozess: Kein fachlicher Schreibprozess. Die internen QS-Skripte lesen CSV-Dateien und melden Struktur-, ID- und Bestandsschutzverletzungen.

Freigegebener Pruefpfad:

```text
data/curriculum_catalog_v1.csv
-> scripts/validate_curriculum_catalog.py
-> scripts/compare_curriculum_catalog.py
-> scripts/next_competency_ids.py
```

Betroffene Datenquellen:

- `data/curriculum_catalog_v1.csv` nur lesend
- Vergleichskopie eines frueheren oder freigegebenen CSV-Katalogs nur lesend

Regel: Vor CSV-Aenderungen wird der aktuelle Katalog validiert. Vor Uebernahme einer neuen Katalogversion wird sie gegen den freigegebenen Altstand verglichen. Bestehende `competency_id`s duerfen niemals fachlich umgedeutet oder wiederverwendet werden; Text-, Hierarchie-, Status- und Stufenaenderungen an bestehenden IDs muessen durch das Vergleichswerkzeug sichtbar werden. Neue Kompetenz-IDs werden mit `scripts/next_competency_ids.py` global fortlaufend vergeben; fachbezogene Nummernkreise und Wiederverwendung von Luecken sind ausgeschlossen. Die QS-Skripte schreiben nicht in SQLite, erzeugen keine Migration und veraendern keine UI-Projektionen.

## Testdaten fuer Laura-Pilottest erzeugen

Start: Fuer einen Pilottest soll die lokale SQLite-Datenbank mit kuenstlichen Daten befuellt werden.

Schreibprozess: Explizites CLI-Script `scripts/seed_test_data.py`.

Freigegebener Testpfad:

```text
python3 scripts/seed_test_data.py
```

Optionaler Reset-Pfad:

```text
python3 scripts/seed_test_data.py --reset
```

Betroffene Datenquellen:

- SQLite `data/kompetenzmanager.sqlite`
- Dateisystem `data/documents/<student_id>/`
- SQLite `timetable_entries`

Erforderliche IDs:

- kuenstliche `student_id`
- bestehende oder kuenstliche `group_id`, `course_id`, `course_group_id`
- kuenstliche `observation_id`
- kuenstliche `document_id`
- kuenstliche `timetable_entry_id`

Automatisch profitierende Ansichten:

- Stammgruppenuebersicht
- Kursuebersicht
- Schuelerprofil
- Beobachtungsdialog
- Berichtsvorbereitung
- Dokumentationsstand
- Dokumente & Medien
- Dashboard und Stundenplan

Regel: Der produktive App-Start erzeugt keine Demo-Schueler. Testdaten werden nur durch das explizite Script erzeugt. Ohne `--reset` bricht das Script ab, wenn bereits Schueler, Beobachtungen oder Dokumente vorhanden sind. Mit `--reset` wird bewusst ein frisches lokales Testsystem erzeugt. Der Pilottest-Seed bildet einen rund achtmonatigen Nutzungsstand bis zum aktuellen Pilotzeitraum ab und enthaelt vier Stammgruppen, mehrere Kurse und Kursverbuende, einen vollstaendigen Wochenstundenplan, fachbezogene Kompetenzbeobachtungen fuer alle aktiven Katalogfaecher, unterschiedliche Beobachtungsdichten, Kompetenzverlaeufe, eindeutige Schnellbeobachtungen, Soft Deletes, bestaetigte Kompetenzstaende sowie Demo-Dokumente. Es werden keine echten Kindernamen und keine echten Dokumente verwendet; Demo-Dateien sind harmlose Platzhalter und werden nicht versioniert.

## Lernentwicklungsbericht-Entwurf speichern

Start: Laura legt aus einem Schuelerprofil einen Lernentwicklungsbericht-Entwurf an oder speichert einen bereits geladenen Entwurf erneut.

Freigegebener Pfad:

```text
PySide Berichtswerkstatt
-> LearningReportDraftViewModel
-> StudentDesktopAdapter
-> Application Command / ReportDraftService
-> SQLiteReportDraftRepository
-> SQLite report_drafts + Relationstabellen
```

Betroffene Datenquellen:

- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`

Erforderliche IDs:

- neuer oder bestehender `report_draft_id`
- bestehender `student_id`
- ausgewaehlte bestehende `subject_id`
- ausgewaehlte bestehende `competency_id`
- ausgewaehlte bestehende `observation_id`

Regel: Anlegen erzeugt genau einen Entwurf mit Status `draft` und unveraenderlichem `created_at`. Aktualisieren ersetzt Fachauswahl, Fachtexte, Kompetenz-, Beobachtungs- und Diagrammreferenzen atomar und setzt `updated_at`. Neue Kompetenzreferenzen muessen aktiv und `current` sein; neue Beobachtungsreferenzen muessen aktiv sein. Beide Referenzarten muessen zum ausgewaehlten Fachkontext gehoeren, Beobachtungen zusaetzlich zum Kind. Bereits im Draft gespeicherte, spaeter deaktivierte Kompetenz- oder soft-geloeschte Beobachtungsreferenzen bleiben beim Speichern erhalten, solange sie nicht ausdruecklich abgewaehlt werden. Kompetenz- und Beobachtungsinhalte werden nicht kopiert. Der Prozess erzeugt keine Bewertung, Bestaetigung, Version, Freigabe, Archivierung oder finale Ausgabe. Das neutrale `ReportOutputModel` wird weiterhin erst fuer die Vorschau beziehungsweise PDF-Ausgabe aus dem geladenen Entwurf und den aktuellen freigegebenen Leseprojektionen gebaut.

## Lernentwicklungsbericht-Entwurf laden

Start: Laura oeffnet einen vorhandenen Entwurf zur Weiterbearbeitung.

Leseweg:

```text
SQLite report_drafts + Relationstabellen
-> SQLiteReportDraftRepository
-> Application Query
-> LearningReportDraftViewModel
-> PySide Berichtswerkstatt
```

Regel: Laden rekonstruiert ausschliesslich gespeicherte manuelle Texte und Referenzen. Kompetenzstatus und Kompetenztexte werden mit den gespeicherten `competency_id`-Werten als `retained_competency_ids` aus der kanonischen Projektion gelesen. Nicht mehr regulaer verfuegbare Kompetenzen bleiben gekennzeichnet ausgewaehlt, koennen nach Abwahl aber nicht neu ausgewaehlt werden. Aktive Beobachtungsinhalte werden aus der bestehenden Beobachtungsprojektion gelesen; gespeicherte, dort nicht mehr aktive `observation_id`-Werte bleiben ohne erfundene Inhalte als nicht verfuegbar sichtbar. Vorschau und `ReportOutputModel` weisen solche Ausfaelle neutral aus.

Beim Öffnen aus dem Schülerprofil zeigt die Shell bei mindestens einem vorhandenen RPD eine bewusste Auswahl: vorhandenen Entwurf nach Zeitraum und Status öffnen, neuen noch ungespeicherten Entwurf beginnen oder abbrechen. Die Auswahl schreibt keine Daten. Ein neuer Zeitraum wird erst über den bestehenden Create-Command als neuer RPD persistiert; er ändert keinen vorhandenen RPD, RPT oder RPV.

## Lernentwicklungsbericht finalisieren und revidieren

Start: Eine verantwortliche Lehrkraft finalisiert bewusst einen vorhandenen `RPD` und uebergibt ihren nichtleeren Anzeigenamen. Es wird keine Benutzer-ID erzeugt oder abgeleitet.

Freigegebener produktiver Pfad:

```text
PySide Berichtswerkstatt
-> LearningReportDraftViewModel speichern
-> StudentDesktopAdapter.prepare_learning_report_finalization
-> ReportFinalizationService.prepare
-> explizite Bestaetigung mit Lehrkraft-Anzeigename
-> StudentDesktopAdapter.finalize_learning_report
FinalizeLearningReportCommand
-> ReportFinalizationApplicationService
-> ReportFinalizationService
-> LearningReportFinalizationValidator
-> LearningReportSnapshotBuilder
-> SQLiteLearningReportRepository
-> SQLite learning_reports + learning_report_revisions
```

Gelesene Datenquellen:

- `report_drafts` und alle `report_draft_*`-Relationen
- `students`, `groups`, `courses`
- `competencies`
- `observations`, `observation_competency_ratings`
- `student_competency_confirmations` ausschliesslich fuer bewusst ausgewaehlte Diagrammwerte

Geschriebene Datenquellen:

- `learning_reports`
- `learning_report_revisions`

Erstfinalisierung:

1. `RPD` und alle referenzierten Quelldaten laden.
2. Zeitraum, Berichtstyp, Fachauswahl, verantwortete manuelle Inhalte sowie Kompetenz- und Beobachtungsreferenzen vollstaendig validieren.
3. Fachlichen Snapshot vollstaendig im Speicher erzeugen.
4. Snapshot kanonisch als UTF-8-JSON serialisieren und SHA-256 ueber exakt diese Bytes bilden.
5. Genau ein `RPT` fuer das Quell-`RPD` und Revision 1 als `RPV` in einer Transaktion schreiben.
6. Bei jedem Fehler die gesamte Transaktion zurueckrollen.

Folgerevision:

1. Dasselbe ueber `source_report_draft_id` gefundene `RPT` verwenden und dessen unveraenderliche Aggregateidentitaet gegen `student_id`, `report_type`, `period_start` und `period_end` des Drafts pruefen.
2. Bei einer Abweichung die Finalisierung als Domainfehler ablehnen; ein anderer Berichtstyp oder Zeitraum braucht einen neuen `RPD` und ein neues `RPT`.
3. Naechste Revisionsnummer und neue globale `RPV`-ID innerhalb der Schreibtransaktion bestimmen.
4. Bisher aktuelle Revision auf `superseded` setzen und `superseded_at` setzen.
5. Neue Revision mit Status `finalized` schreiben.
6. Bei jedem Fehler bleibt die bisherige Revision unveraendert aktuell.

Validierungsregeln:

- Draft, Student, unterstuetzter Berichtstyp und gueltiger Zeitraum muessen existieren beziehungsweise gueltig sein.
- Mindestens ein Fach und mindestens ein nichtleerer, manuell verantworteter Gesamt- oder Fachtext sind erforderlich.
- Alle Kompetenzreferenzen muessen vollstaendig aufloesbar und einem ausgewaehlten Fach zugeordnet sein. Bereits im Draft gespeicherte inaktive oder `legacy`-Kompetenzen duerfen mit Historienkennzeichnung eingefroren werden.
- Alle Beobachtungsreferenzen muessen aktiv, dem Kind zugeordnet und ueber Beobachtungsfach oder Kompetenzbewertung mindestens einem ausgewaehlten Fach fachlich zuordenbar sein. Fehlende oder inaktive `OBS`-IDs blockieren bis zur ausdruecklichen Abwahl im Draft.
- Bestaetigte Kompetenzstaende sind keine allgemeine Finalisierungspflicht.

Regel: Der `RPD` bleibt nach jeder Finalisierung im Status `draft` und normal bearbeitbar. Seine spaeteren Text- und Referenzaenderungen duerfen eine Folgerevision erzeugen, seine nach Revision 1 abweichenden Angaben zu Berichtstyp oder Zeitraum aber nicht dasselbe `RPT` umdeuten. `learning_reports` wird nach seiner Erstellung weder aktualisiert noch geloescht. Spaetere Aenderungen an Draft, Student, Kompetenz, Beobachtung oder Projektionen veraendern keine bestehende `RPV`. PDF-Artefakte, Renderer-Versionierung, Archivierung und LEG-Abschluss sind nicht Bestandteil dieses Schreibprozesses.

Produktive UI-Regel Sprint 5B.3: Vor jeder Bestaetigung wird der aktuelle Widgetstand ueber den bestehenden Draft-Lifecycle gespeichert. `ReportFinalizationService.prepare` validiert danach denselben gespeicherten Stand und erzeugt die Zusammenfassung fuer Kind, Berichtstyp, Zeitraum, Faecher, Kompetenz- und Beobachtungsanzahl sowie neue Revisionsnummer. Der Anzeigename wird sinnvoll aus `report_drafts.teacher_name` vorbelegt, bleibt aber eine verpflichtende freie Anzeigeeingabe ohne Benutzer- oder Rollen-ID. Erst eine ausdrueckliche Checkbox-Bestaetigung loest den bestehenden transaktionalen Finalisierungscommand aus. Bei fachlichen Fehlern bleibt die aktuelle Revision unveraendert und die Berichtswerkstatt zeigt eine handlungsorientierte `InlineMessage`; nur unerwartete technische Fehler sind modal. Es wird kein PDF automatisch erzeugt.

## Lernentwicklungsbericht-Revisionen und Snapshot lesen

Start: Laura oeffnet die Berichtswerkstatt oder waehlt eine konkrete `RPV`-Revision.

Status- und Historienweg:

```text
PySide Berichtswerkstatt
-> StudentDesktopAdapter.learning_report_revision_status(report_draft_id)
-> ReportRevisionApplicationService
-> LearningReportRevisionReadService
-> SQLiteLearningReportRepository
-> learning_reports + learning_report_revisions
```

Regel: Der Leseservice ermittelt das `RPT` zu einem `RPD`, die aktuelle `finalized`-Revision und alle Revisionen neueste zuerst. Fuer `Entwurf geändert` baut er den aktuellen Finalisierungskandidaten mit dem gespeicherten Anzeigenamen und Finalisierungszeitpunkt der aktuellen Revision deterministisch auf und vergleicht dessen SHA-256 mit `snapshot_sha256`. Fachliche Validierung und Vergleich finden zentral statt; die UI liest weder SQLite noch Repositorydetails.

Einzelrevisionsweg:

```text
RPV-ID
-> StudentDesktopAdapter.load_learning_report_revision
-> ReportRevisionApplicationService.snapshot_payload
-> LearningReportRevisionReadService
-> gespeicherten SHA-256 pruefen und snapshot_json lesen
-> LearningReportRevisionViewModel + snapshotbasiertes ReportOutputModel
-> LearningReportRevisionDialog
```

Regel: Nach der `RPV`-Abfrage werden keine operativen Datenquellen gelesen. Namen, Gruppen-/Kurskontext, Fachlabels, Kompetenztexte, Beobachtungsinhalte und Diagrammwerte stammen ausschliesslich aus dem Snapshot. Die Ansicht ist vollstaendig schreibgeschuetzt. Ein fehlgeschlagener Hash verhindert das Oeffnen; aktuelle Daten werden niemals als Ersatz rekonstruiert.

## Finales Lernentwicklungsbericht-PDF erzeugen

Start: Laura oeffnet eine konkrete aktuelle `RPV`-Revision und waehlt `Finales PDF erstellen`.

Freigegebener Pfad:

```text
LearningReportRevisionDialog (RPV-ID)
-> StudentDesktopAdapter.generate_learning_report_pdf
-> LearningReportPdfApplicationService
-> LearningReportPdfService
-> LearningReportRevisionReadService + SQLiteLearningReportRepository
-> gespeicherten RPV-Snapshot und SHA-256 validieren
-> snapshotbasiertes ReportOutputModel
-> reiner PdfRenderer
-> verwaltete PDF-Datei
-> SQLiteLearningReportPdfArtifactRepository
-> learning_report_pdf_artifacts
```

Gelesene Datenquellen:

- `learning_reports`
- `learning_report_revisions`
- eine bereits vorhandene `learning_report_pdf_artifacts`-Zeile fuer idempotente Wiederaufrufe

Geschriebene Ziele:

- PDF-Datei unter `data/documents/<student_id>/reports/<RPT>/<RPV>/`
- genau eine unveraenderliche Zeile in `learning_report_pdf_artifacts` pro `RPV`

Regeln:

1. Nur eine Revision mit aktuellem Status `finalized` darf ein neues Artefakt erzeugen. Draft und `superseded` sind unzulaessig.
2. Vor dem Rendern werden gespeicherter Snapshot-Hash, Schemaversion, Pflichtstruktur und interne Fach-, Kompetenz-, Beobachtungs- und Textreferenzen geprueft. Es werden keine operativen Quellen nachgeladen.
3. Der vorhandene `PdfRenderer` erhaelt ausschliesslich das aus diesem Snapshot gebaute `ReportOutputModel` und kennt keine Persistenz- oder Statuslogik.
4. Nach erfolgreichem Rendern werden PDF-SHA-256 und Dateigroesse berechnet. Erst danach wird die `RPA`-Referenz gespeichert.
5. Ein vorhandenes Artefakt wird nie ueberschrieben. Der Wiederaufruf bestaetigt relativen Pfad, Dateigroesse und PDF-Hash und gibt dieselbe Referenz zurueck.
6. Draftaenderungen, operative Datenaenderungen und spaetere Revisionen veraendern bestehende PDF-Dateien und Hashes nicht.
7. Bei Render-, Datei-, Hash- oder Persistenzfehlern entsteht keine gueltige neue Artefaktreferenz; eine in diesem Versuch erzeugte Datei wird entfernt.

Renderer-Versionierung, Mehrfachartefakte, komplexe Archivverwaltung, LEG-PDF und externe freie Exportpfade sind nicht Bestandteil dieses Lifecycles.

## LEG-Arbeitsentwurf speichern

Start: Laura legt fuer einen Schueler einen Lernentwicklungsgespraech-Arbeitsentwurf an oder speichert einen bereits geladenen Entwurf erneut.

Freigegebener Pfad:

```text
LEG ViewModel
-> StudentDesktopAdapter
-> LearningConferenceDraftApplicationService
-> LearningConferenceDraftService
-> SQLiteLearningConferenceDraftRepository
-> SQLite learning_conference_drafts + Relationstabellen
```

Betroffene Datenquellen:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Erforderliche IDs:

- neuer oder bestehender `learning_conference_draft_id`
- bestehender `student_id`
- ausgewaehlte bestehende `subject_id`
- ausgewaehlte bestehende `competency_id`
- ausgewaehlte bestehende `observation_id`

Regel: Anlegen erzeugt genau einen Entwurf mit Status `draft` und unveraenderlichem `created_at`. Aktualisieren ersetzt manuelle Inhalte sowie Fach-, Themen-, Kompetenz-, Beobachtungs- und Diagrammreferenzen atomar und setzt `updated_at`. `student_id` bleibt stabil. Neue Beobachtungsreferenzen muessen aktiv sein und zum Kind gehoeren. Bereits referenzierte, spaeter soft-geloeschte Belege bleiben erhalten und werden beim Laden als nicht verfuegbar gekennzeichnet. Der Prozess erzeugt keine Kompetenzbewertung, keinen Kompetenzstatus, keine automatischen Texte, keine finale Version, Freigabe oder Archivierung.

## LEG-Arbeitsentwurf laden

Start: Laura oeffnet einen vorhandenen Entwurf zur Weiterbearbeitung.

Leseweg:

```text
SQLite learning_conference_drafts + Relationstabellen
-> SQLiteLearningConferenceDraftRepository
-> Application Query
-> LearningConferenceDraftViewModel
-> produktiver Sprint-7G.2-LEG-Arbeitsbereich
```

Regel: Laden rekonstruiert manuelle Inhalte und stabile Referenzen. Kompetenzstatus, Kompetenztexte und Beobachtungsinhalte werden aus den bestehenden Live-Sources-of-Truth neu projiziert. Nicht mehr aktive Beobachtungsbelege werden weder verworfen noch ersetzt, sondern kontrolliert als nicht verfuegbar ausgewiesen. Der Draft ist kein eingefrorener Gespraechsstand.

Sprint 7G.2 startet diesen Prozess im Schuelerprofil ueber `Lernentwicklungsgespräch`. Bei mindestens einem vorhandenen Draft muss Laura einen vorhandenen Entwurf öffnen, ein neues eigenständiges LEG beginnen oder abbrechen. Die Auswahl schreibt keine Daten; das neue LEG wird erst über den bestehenden Create-Command als eigener LCD persistiert und ist keine Revision eines vorhandenen LCF/LCV. Die Dialogaktion `Entwurf speichern` darf jederzeit ausgefuehrt werden; Schliessen allein erzeugt keine finale Dokumentation und fuehrt keine stillschweigende Speicherung aus.

## Kompetenz aendern

Start: Name, Beschreibung, Hierarchie oder Status einer bestehenden Kompetenz wird angepasst.

Schreibprozess: Kompetenzverwaltung / Lehrplanpflege, spaeter freizugeben.

Betroffene Datenquellen:

- `data_competencies`
- optional `data_subjects`

Erforderliche IDs:

- bestehender `competency_id`
- gueltiger `subject_id`
- optional gueltiger `parent_competency_id`

Automatisch profitierende Ansichten:

- Beobachtungsdialog
- Kompetenzansicht
- Schuelerprofil
- Berichte
- Dashboards

Regel: `competency_id` bleibt erhalten. Alte grobe Kompetenzen duerfen spaeter deaktiviert oder archiviert werden, aber nicht geloescht werden, solange historische Beobachtungen oder bestaetigte Kompetenzstaende darauf verweisen. Bestehende `observation_competency_ratings` bleiben gueltig und werden nicht automatisch auf spaetere konkrete Kompetenzen migriert. Offene Entscheidung fuer einen spaeteren Implementierungssprint: historische Beobachtungen zeigen entweder das aktuelle Kompetenzlabel oder das zum Beobachtungszeitpunkt gueltige Label.

## Schuelerdokument hinzufuegen

Start: Zu einem Schueler wird ein Hauptdokument referenziert.

Schreibprozess: Schuelerverwaltung / Dokumentenfunktion, spaeter freizugeben.

Betroffene Datenquellen:

- `data_media`

Erforderliche IDs:

- neuer `media_id`
- bestehender `student_id`

Automatisch profitierende Ansichten:

- Schuelerverwaltung
- Schuelerprofil
- Berichte

Regel: Das Dokument liegt im Dateisystem unter `Dokumente/<student_id>/Hauptdokumente/`. Excel speichert nur `file_ref` und Metadaten. Kein Dokument wird in Excel eingebettet.

## Beobachtungsanhang hinzufuegen

Start: Zu einer Beobachtung wird eine Anlage hinzugefuegt.

Schreibprozess: Medienfunktion, spaeter freizugeben.

Betroffene Datenquellen:

- `data_media`

Erforderliche IDs:

- neuer `media_id`
- bestehender `student_id`
- bestehender `observation_id`

Automatisch profitierende Ansichten:

- Schuelerprofil
- Beobachtungsdetails
- Berichte

Regel: Beobachtungsanhaenge liegen im Dateisystem unter `Dokumente/<student_id>/Beobachtungsanhaenge/<observation_id>/`. Excel speichert nur `file_ref` und Metadaten. Medien referenzieren Beobachtungen und speichern keine Beobachtungsinhalte doppelt.

## Lernentwicklungsgespraech abschliessen

Start: Die verantwortliche Lehrkraft loest fuer einen gespeicherten `LCD` ausdruecklich `Gespraech abschliessen` aus. Die UI uebergibt nur die LCD-ID.

Schreibprozess:

1. `LearningConferenceCompletionApplicationService` laedt den aktuellen LCD und alle bewusst ausgewaehlten Referenzen ueber das LEG-Repository.
2. Die LEG-Domain validiert Schuelerbezug, Gespraechsdatum, verantwortliche Lehrkraft, mindestens einen gemeinsamen Ergebnisinhalt und die vollstaendige Aufloesbarkeit aller Abschlussreferenzen.
3. Der LEG-spezifische Snapshot Builder erzeugt ausschliesslich aus diesen validierten Daten die kanonische Snapshotstruktur. Interne Vorbereitung, private Notizen und Diagrammtypen werden nicht uebernommen.
4. Aus kanonischem UTF-8-JSON wird SHA-256 berechnet.
5. Das SQLite-Repository erzeugt beim ersten Abschluss LCF und LCV atomar. Bei einer Korrektur schreibt es zuerst die neue Revision und ersetzt den Status der bisherigen Revision innerhalb derselben Transaktion; bei einem Fehler wird alles zurueckgerollt.
6. Entspricht der Hash dem aktuellen Snapshot, wird die bestehende LCV zurueckgegeben und keine neue Revision erzeugt.

Betroffene Datenquellen:

- lesend: `learning_conference_drafts` und Relationen, `students`, `groups`, `courses`, `competencies`, `observations`, `observation_competency_ratings`
- schreibend: `learning_conferences`, `learning_conference_revisions`

Erforderliche IDs:

- bestehende `learning_conference_draft_id`
- neue `learning_conference_id` beim ersten Abschluss
- neue `learning_conference_revision_id` nur bei neuem Snapshot

Regeln:

- LCD bleibt nach jedem Abschluss bearbeitbar und wird nicht umgedeutet.
- Alte Revisionen werden erst nach einem vollstaendig erfolgreichen Folgeabschluss `superseded`.
- Abgeschlossene Revisionen werden weder geloescht noch inhaltlich aktualisiert.
- Fehlende ausgewaehlte Fach-, Kompetenz- oder Beobachtungsreferenzen werden nicht still entfernt.

## LEG-Abschlussrevision anzeigen

Start: Eine LCV wird aus der Abschluss- beziehungsweise Revisionshistorie geoeffnet.

Leseprozess:

1. Adapter und Application Service laden die LCV ueber das Repository.
2. Der LEG-Leseservice bildet aus dem gespeicherten Snapshot-JSON erneut die kanonischen Bytes und prueft SHA-256 sowie Snapshot-Schemaversion.
3. Das ViewModel projiziert ausschliesslich diese Snapshotdaten in die schreibgeschuetzte Ansicht.

Regel: Es werden keine aktuellen Schueler-, Gruppen-, Kurs-, Kompetenz- oder Beobachtungswerte nachgeladen. Ein Integritaetsfehler verhindert die Anzeige.

## Finales LEG-PDF erzeugen

Start: Laura oeffnet eine konkrete aktuelle LCV mit Status `completed` und waehlt `Finales PDF erstellen`.

Freigegebener Pfad:

```text
LearningConferenceRevisionDialog (LCV-ID)
-> StudentDesktopAdapter.generate_learning_conference_pdf
-> LearningConferencePdfApplicationService
-> LearningConferencePdfService
-> LearningConferenceRevisionReadService + SQLiteLearningConferenceRepository
-> gespeicherten LCV-Snapshot und SHA-256 validieren
-> LEG-spezifisches renderer-neutrales Ausgabemodell
-> reiner PdfRenderer
-> verwaltete PDF-Datei
-> SQLiteLearningConferencePdfArtifactRepository
-> learning_conference_pdf_artifacts
```

Gelesene Datenquellen:

- `learning_conference_revisions`
- `learning_conferences`
- eine vorhandene `learning_conference_pdf_artifacts`-Zeile fuer idempotente Wiederaufrufe

Geschriebene Ziele:

- PDF-Datei unter `data/documents/<student_id>/learning_conferences/<LCF>/<LCV>/`
- genau eine unveraenderliche Zeile in `learning_conference_pdf_artifacts` pro LCV

Regeln:

1. Nur eine LCV mit aktuellem Status `completed` darf ein neues Artefakt erzeugen. LCD und `superseded` sind unzulaessig.
2. Der LEG-Revisionsleseservice prueft kanonisches Snapshot-JSON, Schemaversion und SHA-256. Danach validiert die PDF-Domain alle fuer die Ausgabe erforderlichen Snapshotstrukturen und Referenzen.
3. Es werden weder LCD noch aktuelle Schueler-, Kompetenz-, Beobachtungs- oder sonstige Live-Projektionen gelesen.
4. Der reine `PdfRenderer` erhaelt nur das aus dem LCV-Snapshot gebaute Ausgabemodell und kennt weder Persistenz, Status noch Hashregeln.
5. Nach erfolgreichem Rendern werden Dateigroesse und PDF-SHA-256 berechnet; erst danach wird die `LCA`-Referenz gespeichert.
6. Ein vorhandenes Artefakt wird nie ueberschrieben. Der Wiederaufruf verifiziert Snapshot-Hash, Pfad, Dateigroesse und PDF-Hash und gibt dieselbe Referenz zurueck.
7. Bei Render-, Datei-, Hash- oder Persistenzfehlern entsteht keine gueltige neue Artefaktreferenz; eine in diesem Versuch erzeugte Datei wird entfernt.

Archivierung, Verschluesselung, Renderer-Versionierung, Mehrfachartefakte, Rollenmodell und Berichtsdomain sind nicht Bestandteil dieses Lifecycles.
