# UI Data Mapping

## V3-only Startup und geplanter Schuljahresassistent

**Status:** SJ-2F ergänzt produktive Final-V3-Writer in vorhandenen
Schüler- und Stammdatenviews. Exakt verifiziertes Final-V3 ist für die
technische Runtime lokal aktiviert. `Einstellungen → Schuljahre` ist
einschließlich der geschützten SJ-3C.6-Ausführung integriert;
Mehrkindwechsel außerhalb dieses Vorgangs bleibt in der UI gesperrt.

Der Datenbankstart zeigt keinen V2-Bootstrap, keine V2-Migrationsvorschau und
keine Auswahl zur Übernahme alter Testdaten. Ein erkanntes, vollständig
verifiziertes Final-V3 erreicht als `V3_SCHEMA_READY` die normale Runtime.
Unbekannte oder beschädigte Schemata führen fail-closed in die bestehende
kontrollierte Recoverygrenze.

Eine fehlende Datenbank darf nur im autorisierten First Run direkt als
Final-V3 erzeugt werden. Sie wird anschließend erneut vollständig geprüft und
von der Composition Root nur mit `create=False` geöffnet. Der First Run
erzeugt kein Schuljahr. Fehlt ein eindeutiges `current`-Schuljahr, startet die
Runtime technisch, während die schülerbezogenen Bereiche mit dem vorhandenen
fachlichen Sperrzustand blockiert bleiben. Synthetische Daten sind kein
Produktdefault.

Der Einstieg unter `Einstellungen → Schuljahre` bereitet ausschließlich die
flüchtige Vorschau eines echten späteren Wechsels vor. Das Zielschuljahr wird
in diesem Zwischenstand noch nicht gespeichert oder aktiviert. Seine
fachlichen UI-Felder bleiben:

Die isolierte SJ-3C.2-Application-/Repository-Transaktion auf temporären
synthetischen Final-V3-Datenbanken ist nicht an diese Oberfläche angebunden
und ergänzt weder Feld noch Aktion.

| UI-Feld/Aktion | Quelle | Persistenz | Regel |
|---|---|---|---|
| Ausgangsschuljahr | vorhandenes eindeutiges `school_years.status = current` | Nein | niemals leer, nicht aus Systemdatum ableiten |
| Zielschuljahr | bewusst eingegebene flüchtige Bezeichnung sowie Beginn und Ende | Nein | Validierung ausschließlich über die vorhandene Preview-Logik; kein automatischer Statuswechsel |
| bisherige Zuordnung | Assignment am Ende des Ausgangsjahres | Nein | keine Schüler-Membershipfelder |
| Zielkursvorschlag | bestätigtes `courses.year_level` | nur im flüchtigen Plan | Stufe 3 bleibt ungelöst; keine Namens-/Sortierableitung |
| Zielstammgruppe | bisherige Stammgruppe oder bewusste Änderung | nur im flüchtigen Plan | keine versteckte Änderung |
| Zielstatus | fortführen, wiederholen, anderer Kurs, ausgeschieden oder ungelöst | nur im flüchtigen Plan | Austritt ist keine Archivierung |
| Backupstatus | verifizierter Sicherheitsbackupnachweis des finalen Schemas | technischer Nachweis | keine V2-Cutover-Evidence |
| verbindlich aktivieren | validierter vollständiger Plan, Step-up und Bestätigung | eine atomare Transaktion | Ausgangsjahr schließen, Zieljahr aktivieren, Assignments und echten Transition-Beleg schreiben |

Die minimale Settings-Integration besitzt aktuell:

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| Navigation `Schuljahre` | lokale Settings-Navigation | Nein | per Maus, Return, Enter und Leertaste erreichbar |
| aktuelles Schuljahr | eindeutiges `SchoolYearRepository.require_current()` über den bestehenden Desktop-Read | Nein | Label und Zeitraum anzeigen; fehlt die Eindeutigkeit, bleibt die Vorbereitung deaktiviert |
| Bezeichnung, Beginn, Ende | bewusste Settings-Eingabe | Nein | Accessible Names; Datumsvorgaben nur aus dem aktuellen Schuljahr, nie aus dem Systemdatum |
| Schuljahreswechsel vorbereiten | Eingaben plus `SchoolYearTransitionPreviewService` | Nein | Preview und flüchtiger Plan entstehen aus demselben `query_only`-Snapshot |
| neutraler Eingabefehler | vorhandene globale Zieljahres-Issues der Preview | Nein | keine technischen Codes, SQL-Texte oder Pfade zeigen |
| vorhandenen Vorschau-/Bearbeitungsdialog öffnen | `SchoolYearTransitionPlan` | Nein | Schließen verwirft den Plan; keine Ausführung, kein Backup, kein Step-up, kein Maintenance-Gate und kein Transition-Beleg |

SJ-3B.1 implementiert davon ausschließlich die rein lesende Vorschau:

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| Kopf mit Ausgangs-/Zieljahr, Zielzeitraum und Zählern | vorhandene `SchoolYearTransitionPreview` | Nein | Zähler nicht im Widget nachberechnen |
| Status | `SchoolYearTransitionPreview.executable` und vorhandene Issue-Texte | Nein | nur `Vorschau vollständig` oder `Entscheidungen erforderlich`; keine Ausführungsfreigabe |
| vollständige Kindtabelle | `SchoolYearTransitionPreview.items` | Nein | jedes Item genau einmal und in vorhandener Reihenfolge; `student_id` ist der einzige in SJ-3B.1 aktuell verwendete Kindbezeichner |
| bisherige und vorgeschlagene Zuordnung | Felder des jeweiligen `SchoolYearTransitionPreviewItem` | Nein | keine zweite Datenquelle und keine fachliche Neuberechnung |
| Zielstatus und Warnungen | `target_status`, `warning_codes`, `blocker_codes` | Nein | ungelöst und alle Issues als sichtbarer Text, nicht nur farblich |
| Schließen | Dialogzustand | Nein | einzige Aktion; kein Refresh, Write, Backup, Step-up oder Ausführungsbutton |

SJ-3B.2a ergänzt noch keine Qt-Bearbeitung, sondern nur das flüchtige
Application-Planmodell:

| Planfeld / Entscheidung | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| Kind für die spätere Qt-Abbildung | `student_id` plus `student_display_name` der Preview | Nein | ID bleibt Identität; fehlender V3-Datensatz liefert neutral `Name nicht verfügbar`; SJ-3B.2a ändert noch kein Qt-Mapping |
| Ausgangsvorschlag | vorhandenes `SchoolYearTransitionPreviewItem` | Nein | Preview und ursprüngliche Issues bleiben unverändert |
| Zielkurs | explizite aktive Kursoptionen | Nein | das Auswahlfeld verwendet ausschließlich kompakte Kursnamen sowie `Verbleibt in <Kurs>`; der aktuelle Zielkurs erscheint nur als gewählter Wert und nicht nochmals in der Optionsliste; `Ausgeschieden` und `Ungelöst` bleiben getrennte sekundäre Statusaktionen, technische Planaktion unsichtbar und unverändert, keine Automatik |
| Zielstammgruppe | explizite aktive Gruppenoptionen | Nein | aktueller Zielwert erscheint nur im Feld; die Optionsliste zeigt ausschließlich andere vorhandene Gruppennamen ohne technische Präfixe |
| ausgeschieden | bewusste Planentscheidung | Nein | besitzt weder Kurs- noch Gruppenanspruch; ist keine Archivierung |
| bearbeitet / unverändert | flüchtiger Entscheidungszustand | Nein | jede Bearbeitung liefert eine neue Planinstanz |
| Validierung und Zähler | aktueller flüchtiger Plan | Nein | deterministisch; keine Ausführungsfreigabe |

SJ-3B.2b stellt diesen flüchtigen Plan im vorhandenen Vorschau-Dialog
individuell bearbeitbar dar:

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| Schülername und bisherige Zuordnung | kopierte Anzeige-Metadaten des jeweiligen `SchoolYearTransitionPlanItem` | Nein | Name statt technischer ID; `student_id` bleibt unsichtbare stabile Identität |
| Zielstatus | aktueller `SchoolYearTransitionPlanItem.target_status` plus kanonische Ausgangs- und Zielkursstufe des vorhandenen Plans | Nein | tatsächliche Stufenbewegung als `Wechsel <Ausgang> → <Ziel>`; identischer Kurs als `Verbleibt in <Kurs>`, anderer Kurs derselben Stufe als `Kurswechsel innerhalb Stufe <n>`; ausgeschieden und bewusst ungelöst bleiben textlich sichtbar, ausschließlich vorhandene Planmethoden |
| Zielstammgruppe | kopierte bisherige Gruppen-ID plus aktuelle Zielgruppe und `SchoolYearTransitionPlan.available_groups` | Nein | eine weiterhin aktive bisherige Gruppe auch ohne automatischen Gruppenvorschlag bewusst unverändert lassen oder andere aktive Gruppe wählen; bei ausgeschieden leer |
| Zielkurs | aktueller Zielkurs plus `SchoolYearTransitionPlan.available_courses` | Nein | keine Option außerhalb des Plans; bei ausgeschieden und ungelöst leer |
| Warnungen und Blocker | ursprüngliche Preview-Issues plus aktuelle `SchoolYearTransitionPlanValidation` | Nein | ursprünglicher und aktueller Zustand textlich unterscheidbar; nie nur farblich |
| Planstatus und Zähler | `SchoolYearTransitionPlan.validate()` | Nein | nach jeder neuen Planinstanz vollständig neu projizieren |
| Auswahlfelder | darstellungsfertige ViewModel-Optionen | Nein | nur bewusste Aktivierung ändert den Plan; Öffnen und Wiederbefüllen bleiben folgenlos |
| Präsentationsschritte `Zuordnungen prüfen` / `Prüfen und aktivieren` | flüchtiger Widgetzustand | Nein | reine Informationshierarchie; Schrittwechsel ändert weder Plan noch Ausführungsfreigabe und fügt keine Wizard-Domainlogik hinzu |
| kompakte Kennzahlen | vorhandene `SchoolYearTransitionPlanCounts` | Nein | ausschließlich 1→2, 2→3, ungelöst, ausgeschieden und Stammgruppenänderungen; vollständige vorhandene Zusammenfassung bleibt im Abschluss erreichbar |
| kombinierbare Filter | aktueller `SchoolYearTransitionPreviewViewModel` | Nein | alle, nur ungelöst, bisheriger Kurs, Zielkurs, bisherige Stammgruppe und Zielstammgruppe; Filterwechsel selektiert nichts und ändert den Plan nicht |
| Zeilenauswahl und Auswahlzähler | stabile `student_id` im flüchtigen Dialogzustand | Nein | Startansicht ist `Nur ungelöst`, `Alle Kinder` erreicht jedes Planitem; einzeln oder alle sichtbaren auswählbar; Status zusätzlich als Checkboxtext und Accessible Name, nicht nur farblich; verdeckte Auswahl bleibt erhalten und sichtbar gezählt |
| Sammel-Zielkurs / -Zielstammgruppe | ausgewählte sichtbare `student_id` plus ausschließlich aktive `SchoolYearTransitionPlan.available_courses` / `available_groups` | Nein | deaktiviert ohne sichtbare Auswahl; mehrere Kinder verlangen Bestätigung; jede Aktion erzeugt einen neuen Plan und lässt nicht ausgewählte oder verdeckte Kinder unverändert |
| Sammel-ausgeschieden / -ungelöst | ausgewählte sichtbare `student_id` | Nein | ausgeschieden entfernt Zielkurs und Zielgruppe; ungelöst entfernt den Zielkurs; Kurs-3-Fälle werden ausschließlich durch bewusste Kurs-3-Auswahl gelöst |
| Schließen | Dialogzustand | Nein | globale Aktionen bleiben Schließen plus Sammelbearbeitung; keine Ausführung, Speicherung, Backup oder Authentifizierung |

SJ-3C.6 ergänzt die finale Schutz- und Ergebnisstufe:

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| Ausgangs-/Zieljahr und Ergebniszahlen | vorhandener Plan beziehungsweise `SchoolYearTransitionExecutionResult` | Nein | einschließlich 1→2, 2→3, Wiederholer, ausgeschieden, Stammgruppenänderungen und ungelöst; keine Widget-Nachzählung |
| `Ich habe alle Zuordnungen geprüft` | bewusste, nicht vorbelegte Eingabe | Nein | wird nach jeder Planänderung verworfen |
| App-Passwort | vorhandener `SchoolYearTransitionStepUpService` | Nein | sensitiv; falscher Wert erreicht Maintenance und Backup nicht |
| `Schuljahr <Label> verbindlich aktivieren` | vollständiger Plan plus Checkbox und Passwort | bestehende atomare Transition | kein Default-/AutoDefault; Enter und Doppelklick starten nicht |
| fünf Statusschritte | Phasencodes des bestehenden Executors | Nein | neutraler Text ohne Prozentbehauptung oder technische Details |
| Erfolg / Fehler | sanitisiertes Worker-Ergebnis | Nein | Backup und Transition bestätigen, neue Vorschau oder Recovery verlangen; keine IDs, Hashes, Pfade oder Exceptions |

Synthetische Initialdaten sind keine UI-Projektion. IDs, Zeitpunkte und
Fixtures werden ausschließlich im Testpfad erzeugt und niemals als
Produktdaten oder Pilotbestand dargestellt.

## SJ-2F Writer-Mapping

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| aktuelles Schuljahr bei Schüleranlage | eindeutiges `school_years.status = current` aus `SchoolYearRepository` | Nein | sichtbar, keine implizite Auswahl; fehlt oder passt es nicht zum Operationstag, beginnt kein Write |
| Vorname, Nachname und Notiz | Benutzereingabe | V3-`students` | Anlage und Stammdatenbearbeitung enthalten keine Membershipfelder |
| Stammgruppe und Kurs bei Schüleranlage | aktive Stammdatenauswahl | initiales `student_school_year_assignments` | gemeinsam mit dem V3-Schüler atomar; kein Schüler ohne gültiges initiales Assignment |
| Stammgruppe und Kurs beim Stammdatenbearbeiten | aktuelle `CurrentStudentMembershipProjection` | Nein | nur Anzeige; Änderung ausschließlich über den getrennten Einzelwechsel |
| Wechselstichtag | bewusste Datumsauswahl in `StudentMembershipChangeDialog` | `student_school_year_assignments` | altes Intervall endet am Vortag, neues beginnt am Stichtag; `NO_CHANGE` mutiert nichts |
| Zielkurs und optionale Zielstammgruppe | aktive Kurs-/Gruppenstammdaten plus aktuelle Zuordnung | `student_school_year_assignments` | Vorschau und bewusste Bestätigung für genau ein Kind; kein Mehrkindwechsel |
| Austritt | expliziter Stichtag in `StudentExitDialog` | `student_school_year_assignments` | erzeugt `exited` ohne Kurs und Gruppe; archiviert nicht |
| Archivieren | getrennte Aktion | V3-`students` | erzeugt kein `exited`, verändert kein Assignment und wird bei aktueller Einschreibung blockiert |
| Kursstufe | bewusste Auswahl `Stufe 1`, `Stufe 2` oder `Stufe 3` | `courses.year_level` | Pflichtfeld; keine Ableitung aus Kursname, Farbe, Sortierung oder Listenposition; gleiche Stufe für mehrere Kurse zulässig |
| Kurs-/Stammgruppenstatus | Stammdatenaktion mit explizitem Operationstag | `courses.active` / `groups.active` | aktuelle oder zukünftige `enrolled`-Referenz blockiert Deaktivierung; keine automatische Umbuchung, historische Assignments bleiben lesbar |

Die Dialoge zeigen fachliche Fehlermeldungen, keine SQL-Fehler, IDs oder
internen Pfade. Die technische Runtime-Aktivierung ändert diese Writer nicht.
Die manuelle macOS-Prüfung dieser UI-Abläufe ist noch offen.

## SJ-2E Assignment-Read-Mapping

**Status:** Verbindlicher, lokal implementierter Vertrag der produktiven
Membership-Reader. Die Runtime-Aktivierung ist nicht Bestandteil von SJ-2E.

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| aktueller `as_of`-Tag | einmalig vom aufrufenden Bildschirm- oder Application-Request gesetzter Kalendertag | Nein | derselbe Tag gilt für den vollständigen aktuellen Bildschirm-Read; Repository, Adapter, ViewModel und Widget bestimmen kein eigenes Systemdatum |
| aktuelle Schülerliste | `CurrentMembershipReadSnapshot` aus `SchoolYearAssignmentReadSession` | Nein | ausschließlich aktive, nicht archivierte `ENROLLED`-Mitglieder des eindeutigen current-Schuljahres; keine V2-Schülerfelder und keine Abfrage je Kind |
| aktuelle Stammgruppen-, Kurs- und Kursverbundzähler | zentral berechnete Counts aus demselben `CurrentMembershipReadSnapshot` | Nein | keine Python-Nachzählung; Kursverbund ist die Schnittmenge seiner registrierten Stammgruppen und Kurse mit aktuellen Assignments |
| aktuelle Profilzuordnung | `CurrentStudentMembershipProjection` aus derselben `SchoolYearAssignmentReadSession` | Nein | `ENROLLED` zeigt Gruppe und Kurs; `EXITED` zeigt `Im aktuellen Schuljahr ausgeschieden`; `NO_ASSIGNMENT` zeigt `Keine aktuelle Zuordnung`; `STUDENT_ARCHIVED` zeigt neutral, dass das Kind nicht aktuell ist |
| Current-Year-Integritätszustand | `CURRENT_SCHOOL_YEAR_MISSING`-/`AMBIGUOUS`-Diagnostik derselben Session | Nein | fehlendes current-Schuljahr oder `AMBIGUOUS` blockiert die aktuelle fachliche Anzeige; keine leere Liste, Nullzählung, technische ID oder Ersatzzuordnung |
| historische Zuordnung eines Berichts | `AssignmentReferenceRequest(request_key, student_id, period_end)` | Nein | ausschließlich `period_end` des fachlich maßgeblichen RPD; kein current-, Last-known-, Systemdatums- oder V2-Fallback |
| historische Zuordnung eines LEG | `AssignmentReferenceRequest(request_key, student_id, conference_date)` | Nein | ausschließlich `conference_date` des fachlich maßgeblichen LEG; kein current-, Last-known-, Systemdatums- oder V2-Fallback |
| historische Zuordnung einer Beobachtung | `AssignmentReferenceRequest(request_key, student_id, observations.date)` | Nein | ausschließlich das gespeicherte Beobachtungsdatum; kein current-, Last-known-, Systemdatums- oder V2-Fallback |
| freies Dokument ohne fachliches Referenzdatum | keine `AssignmentReferenceRequest` | Nein | Zuordnung bleibt neutral; Dateizeit, Uploadzeit, current und Last-known sind keine Ersatzquelle |

Alle zusammengesetzten Schüler-, Dashboard-, Onboarding-, Beobachtungs-,
Bericht- und LEG-Reads verwenden ihre `SchoolYearAssignmentReadSession` auf
derselben aufrufereigenen Connection und im selben SQLite-Read-Snapshot wie
die übrigen Daten des Requests. Die Session besitzt keine
Transaktionssteuerung. Finalisierte Revisionen und PDFs werden nicht live neu
aufgelöst. Dieses Mapping führt keine neue Tabelle, Migration oder Persistenz
ein. Die getrennte `V3_SCHEMA_READY`-Disposition verändert die fachlichen
Reader- und Sperrverträge nicht.

## Phase 2 Berichte-Übersicht - implementiert

| Sichtbares UI-Feld / Aktion | Quelle | Persistenz | Verbindliche Regel |
|---|---|---|---|
| Berichtszeitraum | `period_start` / `period_end` des eindeutig gewählten RPD | Nein | einziger inklusiver Zeitraum; ohne eindeutigen RPD keine inhaltliche Phase-2-Anzeige; keine Schuljahres- oder Kalenderjahresannahme |
| Timeline | `ReportOverviewViewModel.timeline_events` | Nein | vollständige ausgewählte Liste mit Zielumfang `15`; alle gültigen Bericht-/LEG-Abschlussereignisse bleiben auch oberhalb von 15 enthalten; nach der Auswahl chronologisch vom ältesten zum neuesten Ereignis; keine Trend-, Rang-, Relevanz- oder Entwicklungsdarstellung |
| Timeline-Ereignistyp | `ReportOverviewTimelineEventViewModel` aus vorhandener stabiler Quellidentität und vorhandenem fachlichem Zeitpunkt | Nein | ausschließlich `Bericht abgeschlossen`, `LEG durchgeführt`, `Beobachtung dokumentiert` oder `Kompetenz bestätigt`; eine Beobachtung, ein Berichtaggregat und ein LEG-Aggregat höchstens einmal; Berichtdatum ist `finalized_at`, LEG-Datum ist `conference_date`; Kompetenzzuordnungen und technische Revisionen erzeugen keine eigenen Karten |
| Timeline-Viewport | vollständige `ReportOverviewViewModel.timeline_events` | Nein | horizontal scrollbar; abhängig von der Breite ungefähr `2`, `4` oder `5` Karten gleichzeitig sichtbar, aber keine Inhalts- oder Projektionsgrenze; Start am neuesten Ende, bewusstes Scrollen zu älteren Ereignissen; kein automatisches Karussell und keine automatische Bewegung |
| Timeline-Steuerung | horizontale Scrollposition und stabile gelieferte Ereignisidentität | Nein | Trackpad, horizontale Scrollbar, sichtbare Links-/Rechtsaktionen und Tastatur; Accessible Names und sichtbarer Fokus; Resize erhält die Position möglichst, Refresh verwendet eine stabile Ereignisidentität als Anker; äußeres vertikales Profilscrolling bleibt bedienbar |
| Kontext einer Beobachtungskarte | vorhandenes Fach, Zuordnungsanzahl, Kompetenzbereich, Thema und kurzer vorhandener Kontext | Nein | nur vorhandene strukturierte Werte; keine Ableitung aus Freitext, Anzeigenamen, Rating oder vermuteter Relevanz; kein einzelner Kompetenztext und keine eigene Zuordnungskarte |
| Kontext einer Bestätigungskarte | vorhandene aktuelle `competency_id` mit kanonischem Kompetenztext | Nein | ausschließlich aktueller sicherer Bestätigungsstand; kein Rating, keine historische Kette und keine Kompetenzinterpretation |
| Kontext einer Dokumentkarte | neutrale Bericht- beziehungsweise LEG-Dokumentart | Nein | keine technische Revisionsbezeichnung, Revisionskarte oder Revisionsgewichtung |
| Zugängliche Timeline-Beschriftung | displayfertiger Ereignistext | Nein | vollständiges Datum, Ereignistyp und vorhandener neutraler Kontext; Monatskürzel allein reichen nicht |
| Leere Timeline | keine geeigneten Ereignisse im RPD-Zeitraum | Nein | Titel `Keine Dokumentationsereignisse im Zeitraum` mit neutralem Hinweis auf die zulässigen vorhandenen Quellen |
| Unvollständig lesbare Dokumentation | `ReportOverviewProjectionWarningViewModel` | Nein | `Dokumentationsdaten konnten nicht vollständig gelesen werden.`; keine Ersatzannahme |
| Kleines Fachsymbol | vorhandene stabile `subject_id` über `REPORT_SUBJECT_SYMBOLS` | Nein | neutrale UI-Hilfe anstelle eines Diagramms; unbekannte Fächer erhalten `•`; keine Fachableitung, Menge, Bewertung oder Statusaussage |
| Dokumentierte Kompetenzen je Fach | `ReportOverviewSubjectDocumentationViewModel` | Nein | `<n> Kompetenzen dokumentiert`; eindeutige aktuelle `competency_id` im RPD-Zeitraum; kein Nenner, `von`, `/`, Prozent, Sollwert oder Restmenge |
| Beobachtungen je Fach | `ReportOverviewSubjectDocumentationViewModel` | Nein | `<n> Beobachtungen im Berichtszeitraum`; je Fach deduplizierte `observation_id`; Schnellbeobachtung zählt ohne Kompetenzzuordnung nur hier |
| Fachkartenreihenfolge | bestehende neutrale kanonische Fachreihenfolge | Nein | niemals anhand der Dokumentationsmenge umsortieren; keine Sortierung nach Beobachtungsanzahl, Kompetenzanzahl, Bestätigungsstand, Aktualität, Rating oder vermeintlicher Wichtigkeit |
| Belegnavigation | displayfertige `evidence_action` mit vorhandener `subject_id` | Nein | `Belege ansehen`; keine automatische Auswahl, Qualitätsaussage oder Rekonstruktion aus sichtbarem Fachtext |
| Absolute Dokumentationssegmente | eindeutige aktuelle dokumentierte `competency_id` der Fachkarte | Nein | genau ein gleich breites neutrales Segment je Kompetenz; keine Restspur, Normalisierung, Schwelle, Bewertungsfarbe, Prozent- oder x/y-Semantik; bei null nur neutraler Text |
| Zugängliche Fachkartenbeschriftung | Fachname und absolute Kompetenzmenge | Nein | `<Fach>: <n> Kompetenzen dokumentiert` |
| Aktueller Bestätigungsstand | kanonische aktuelle sichere Kompetenzstatusprojektion | Nein | `aktuell bestätigter Stand vorhanden`; kein Rating, keine Anzahl, Historienrekonstruktion, Zielerreichung oder Abschluss |
| Bericht-/LEG-/Belegnavigation | vorhandene Student-, Draft-, Revisions-, Fach-, Beobachtungs- oder Kompetenz-ID | Nein | öffnet ausschließlich vorhandene Ziele; keine automatische Auswahl oder Inhaltserzeugung |

Sind weniger als 15 verpflichtende Bericht-/LEG-Abschlussereignisse vorhanden,
wählt das ViewModel ausschließlich die zeitlich neuesten zulässigen
Beobachtungs- und sicheren Bestätigungsereignisse
bis zum Zielumfang aus. Bei identischem fachlichem Zeitpunkt gilt die
aufsteigende lexikografische Quellidentität. Das Widget trifft keine
Inhaltsauswahl und entfernt oder priorisiert keine gelieferten Ereignisse.

Historische Kompetenzen werden in Phase 2 weder als aktueller Zählwert noch als
Segment dargestellt. Eine historische Darstellung ist keine aktuell
implementierte Phase-2-Funktion und mit diesem Vertrag weder zur Darstellung
noch zur Aufnahme in aktuelle Zähler freigegeben. Falls eine solche
Darstellung später separat freigegeben wird, muss sie gleichzeitig die beiden
sichtbaren Klarstellungen `Historisch dokumentiert` und
`Nicht aktueller Bestand` enthalten. Dies ist ausschließlich der verbindliche
Neutralitätsvertrag für diesen bedingten späteren Fall und keine
Funktionsfreigabe. `documented_count/current_count`,
`StudentProfileDashboardViewModel.orientation_changes` und technische
`persistence_events` bleiben ausschließlich Teil des dokumentierten
Paket-1-/anderen Produktkontexts und sind keine Phase-2-UI-Quelle.

## Berichte-Übersicht 0.3.1 / Paket 1

Die folgende Tabelle dokumentiert die historische Paket-1-Basis. Die dortige
Meilenstein- und Ringdarstellung ist im sichtbaren Berichtsbereich durch das
vorstehende Phase-2-Mapping ersetzt.

| UI-Feld/Aktion | Quelle | Persistenz | Regel |
|---|---|---|---|
| Berichtstatus | RPD-Liste + getrennte RPT-/RPV-Revisionsprojektion | Nein | kein, eindeutig, mehrdeutig, geändert, finalisiert oder Integritätsfehler; niemals im Widget berechnet |
| Berichtszeitraum | `report_drafts.period_start` / `period_end` des eindeutig gewählten RPD | Nein | einzige Zeitgrundlage; keine Schuljahresbehauptung und keine inhaltliche Projektion ohne eindeutigen RPD |
| Berichtaktion | Anzahl eindeutiger RPD + bestehende Shell-Aktionen | Nein | `Bericht erstellen`, `Bericht öffnen` oder `Bericht auswählen`; mehrere Drafts werden nie still aktiviert |
| LEG-Status | LCD-Liste + getrennte LCF-/LCV-Revisionsprojektion | Nein | ohne Draft `LEG beginnen`, mit eindeutigem Draft `LEG öffnen`, bei Mehrdeutigkeit `LEG auswählen`; keine Berichtsdaten |
| Nächste Schritte | bestehende Draft-/Revisionszustände und vorhandene Navigation | Nein | ausschließlich konkrete Aktionen; keine Empfehlung, Priorisierung oder automatische Auswahl |
| Bericht-/LEG-Historie | getrennte RPD-/RPV- und LCD-/LCV-Leseprojektionen | Nein | gemeinsames Display mit sichtbarem Dokumenttyp; technische IDs verborgen |
| Fachübersicht | vorhandene `LearningReportPreparationViewModel.subjects` mit `documented_count`, `current_count` und fachbezogenen Evidence-Zeilen | Nein | zunächst höchstens vier Fächer in vorhandener Reihenfolge, alle weiteren nur nach lokaler bewusster Erweiterung; neutrales Kreisdiagramm wie im Schülerprofil, Kompetenz- und Beobachtungsanzahl sowie Sprunganker; keine qualitative Bewertung, Empfehlung oder Auswahl |
| `Bericht vorbereiten` | `subject_id` + eindeutiger RPD-Zustand | Nein | jeder neue Draft verlangt unabhängig von vorhandenen Drafts zuerst eine bewusste, nicht persistente Zeitraumauswahl; bei einem Draft direkt, bei mehreren nach Wahl eines vorhandenen Drafts oder zusätzlicher Zeitraumwahl für `Neuer Entwurf` in den vorhandenen Editor auf `Kompetenzen & Belege`/Fach fokussieren; keine Kompetenzübernahme |
| Meilensteinleiste | vorhandene Bericht-/LEG-Historieneinträge + reale datierte Bestätigungsereignisse aus `StudentProfileDashboardViewModel.orientation_changes` | Nein | zeitlich geordnet und abhängig vom verfügbaren Platz auf die neuesten Einträge begrenzt; sichtbare Monatskürzel, verbundene Marker und vorhandene typspezifische Icons; `Kompetenz bestätigt` ist kein Kompetenzabschluss; keine Zeitleistenberechnung |
| Stärken / Im Blick behalten | keine Paket-1-Datenquelle | Nein | klarer neutraler Leerzustand; keine Schwellen, Scores, Kandidaten oder Pädagogiklogik |
| Berichtarbeitsraum-Grenze | vorhandener `LearningReportDialog` | bestehender Draftpfad erst nach bewusster Aktion | kein zweiter Editor; keine eigene untere Übersichtskarte mehr |

## Pilot-Releaseautomation - keine Produktprojektion

Releasekonfiguration, Manifest, Phasen, Assethashes, GitHub-/Appcast-Zustände,
Signaturen, Fehlerdetails und Veröffentlichungsfreigaben werden nicht in
PySide, Einstellungen, Über-Dialog oder Startup projiziert. Die Automation ist
ausschließlich terminalbasiert und ergänzt keine UI-Felder, Aktionen oder
Persistenz. Die bestehende sichtbare Version-/Buildprojektion bleibt direkt an
`src.version` gebunden.

## P1-Paket 1 - sichtbarer unklarer Bestätigungsstand

| UI-Feld/Aktion | Quelle | Persistenz | Regel |
|---|---|---|---|
| Bestätigungsfrische | kanonische `StudentCompetencyStatusViewModel.documentation_state` aus `persistence_events` | Nein | technische Sequenz statt fachlichem Beobachtungsdatum |
| Historischer Gleichstand | `documentation_state = confirmation_unknown` | Nein | sichtbar exakt `Bestätigungsstand unklar – bitte erneut bestätigen`; weder bestätigt noch sicher neu |
| Erneut bestätigen | bestehende Bestätigungsaktion mit stabilem Operation-Token | `student_competency_confirmations` + `persistence_events` | neue Confirmation-Sequenz löst `confirmation_unknown` eindeutig auf |
| Beobachtung speichern | `ObservationDraftViewModel.operation_token` -> `ObservationPersistenceUnitOfWork` | Observation, Ratings, Ereignisse, Dokumentreferenzen | Retry setzt denselben Vorgang fort; keine zweite Beobachtung |

Profil, Kompetenz-Cockpit, Berichtsvorbereitung und LEG übernehmen dieselbe
kanonische Semantik. Eigene Anzeigechronologien dürfen weiterhin fachliche
Beobachtungsdaten sortieren, aber niemals die Bestätigungsfrische ableiten.
Journalphasen, Hashes, Pfade, Inodes und Recoverydetails werden nicht sichtbar
projiziert.

## Releasebasis 0.3.0 / Build 303

| UI-Feld/Aktion | Quelle | Persistenz | Regel |
|---|---|---|---|
| Deutsche Bestätigungsaktion | lokaler `QMessageBox`-Bedienzustand | Nein | Jede Produktbestätigung verwendet einen verständlichen Aktions- und Abbrechen-Text; Escape und Enter führen nicht unbemerkt zur verwerfenden Aktion. |
| Passwort / Passwortbestätigung | temporärer `QLineEdit`-State | Nein | Qt markiert die Eingabe als verborgen, sensitiv, nicht vorhersagbar und ohne Auto-Großschreibung; Einfügen und explizites Anzeigen bleiben möglich. Ein nativer macOS-Passwortvorschlag ist erst nach echtem Bundle-Test bestätigt. |
| Touch-ID-Verfügbarkeit | `DeviceCredentialService.status` | Nein | Auf unterstützten Macs bleibt die Option mit einem konkreten Verfügbarkeitsgrund sichtbar. Aktiviert werden kann sie nur mit aktivem Credential, verfügbarem Secret, eingerichteter Touch ID und bestätigtem Passwort. Eine aktivierte Präferenz führt beim Start in den Auth-Dialog statt in die automatische Geräteanmeldung. |

Es entstehen keine neuen Datenquellen, kein Credential-Material in
`app-preferences.json` und keine neue Fach- oder Security-Persistenz.

## Security Sprint 12 - Versionsprojektion im Über-Dialog

| UI-Feld | Quelle | Persistenz | Regel |
|---|---|---|---|
| Version / Build | `APP_VERSION` und `APP_BUILD_VERSION` aus `src.version` | Nein | read-only; identisch zu Bundle-, Update- und Releasemetadaten |

Gate, SQLCipher-/libsodium-Status, Keychain-Testzustand, Testpfade,
Architekturen und Paketprüfungen werden nicht in der normalen UI angezeigt.

## DMK-Database-Key-Runtime - keine UI-Projektion

Gate, Keyset-Publishphase, Keychain-Zustand, Database-Context, IDs,
Generationen, Fingerprints, Envelope, Registry, technische Pfade und
Fehlercodes werden nicht in PySide projiziert. Es entstehen keine Felder,
Dialoge, Buttons, Einstellungen, Startupmeldungen oder Recoveryaktionen. Die
strukturierte technische Runtimeentscheidung gehört ausschließlich zu
internen Tests.

## Final-V3-SQLCipher-Runtime - keine UI-Projektion

Zusätzliches Gate, Rootmarker, Authentifizierungsbestätigung, technischer
First-Run-Status, Cipher-/SQLite-Version, Integritätsstatus und keyed
Kompatibilitätsreport werden nicht in PySide projiziert. Es entstehen keine
Felder, Dialoge, Buttons, Einstellungen, Startupmeldungen oder
Recoveryaktionen. Die vorhandenen Desktop-Adapter und ViewModels werden nur
im markergebundenen Anwendungssmoke mit der verifizierten `SQLiteDatabase`
komponiert; ihre sichtbaren Fachverträge bleiben unverändert.

## Final-V3-Dokumentcontainer-Runtime - keine UI-Projektion

Document-/Storage-/Key-IDs, Generationen, Envelope-Revision, Containerformat,
Größen, Hashes, MIME, Lifecycle, Gate-, Schema-, Context-, Pointer- und
Crashzustände werden nicht in PySide projiziert. Es entstehen keine Felder,
Dialoge, Aktionen, Anhänge, PDF-Verknüpfungen, Exporte, Vorschauen,
QDesktopServices-Aufrufe oder Recoveryanzeigen. Der injizierte Consumer ist
eine rein technische Testgrenze und kein ViewModel oder Produktviewer.

## Security Sprint 11 - keine sichtbare Produktprojektion

Das interne Gate, die Integrationsphasen, Schema-/Key-/Storage-IDs,
Journal-/Replay-Zustände, Hashes, Pfade, Retained-/Quarantänedetails und
technischen Fehlercodes werden nicht in PySide projiziert. Es entstehen keine
neuen Felder, Dialoge, Buttons, Menüpunkte, Startupmeldungen oder
Einstellungen.

Der bewusste Klartextexport wird in Sprint 11 ausschließlich über den
Qt-freien Application Adapter getestet. Sein fester Hinweis lautet: `Die
exportierte Datei liegt außerhalb des verwalteten Speichers unverschlüsselt
vor.` Eine spätere sichtbare Produktaktion benötigt eine eigene
Product-Owner-/UX-Freigabe und ein neues Mapping. Normale Dokument-, Backup-,
Restore-, Passwortwechsel- und Support-Reset-Oberflächen bleiben unverändert.

## Security Sprint 10 - keine UI-, Startup- oder Dokumentprojektion

Writer, Headerprüfung, Verifier, Reader, Testexport, Rewrap,
Generationsaustausch, Storage-Inventar sowie Envelope-, Manifest-, Chunk- und
Fehlerzustände des isolierten verschlüsselten Dokumentcontainers werden nicht
in PySide, ViewModels, Desktop-Adapter, Startup, Login, Einstellungen,
Schülerprofil, Beobachtungsdialog, Produktviewer, Export oder Backup/Restore
projiziert. Es entstehen keine sichtbaren Felder, Aktionen, Fortschrittsphasen,
Pfadwähler, Vorschauen, Cleanup-Buttons oder automatischen
Migrationszustände.

Eine spätere Produktintegration muss den bewussten Klartextexport und dessen
Hinweis, dass die Datei außerhalb der App unverschlüsselt ist, separat
freigeben. DMK, Wrapping-Key, Document-Key, Envelope, interne IDs,
Containerhashes und Dateisystemdetails bleiben unsichtbar.


## Security Sprint 7B - Keine UI- oder Startup-Projektion

Security Sprint 7B ergänzt keine sichtbaren Felder, Aktionen, Dialoge,
Meldungen, Einstellungen, Navigation oder Startupzustände. Locktransitionen,
Preflight-Modus und Migrations-Crossbinding werden nicht in die Produkt-UI
projiziert. Eine spätere Integration benötigt eine eigene
Product-Owner-Freigabe und ein neues Mapping.

## Security Sprint 6 - Keine UI- oder Startup-Projektion

Security Sprint 6 ergänzt keine UI-Felder, Aktionen, Anzeigen, Dialoge,
Einstellungen oder Startupzustände. Anchor-Revisionen, Lock-Owner,
Journalphasen, Recovery-Schritte, Crashpunkte und technische Fehlercodes werden
nicht in PySide projiziert. Login, Passwortwechsel, Auth-Recovery-Codes, Touch
ID, Support-Reset, Backup/Restore und normale Navigation importieren oder
starten die Foundation nicht. Retained Quarantine besitzt keine Anzeige oder
Cleanup-Aktion. Der Sprint-6-Nachweis erzeugt ausdrücklich keine sichtbare
Verschlüsselungs-, Cleanup- oder Produktfreigabe.

## Security Sprint 5 - Keine UI- oder Startup-Projektion

Security Sprint 5 ergänzt keine UI-Felder, Aktionen, Anzeigen, Dialoge,
Einstellungen oder Startupzustände. Envelope-Lifecycle, Journalphasen,
Recovery-Entscheidungen, Schlüssel-IDs und technische Fehlercodes werden nicht
in PySide projiziert. Login, Passwortwechsel, Recovery-Codes, Support-Reset,
Backup/Restore und normale Navigation importieren oder starten die Foundation
nicht.

## Security Sprint 4 - Keine UI- oder Startup-Projektion

Der Migrationsprototyp ergänzt keine UI-Felder, Aktionen, Statusanzeigen,
Dialoge, Einstellungen oder Startupzustände. Es gibt keine sichtbare
Verschlüsselungsumschaltung und keine Schlüsselabfrage. Login, Recovery,
Touch ID, Support Reset, Backup/Restore und normale fachliche Navigation
importieren oder starten den Prototyp nicht.

## Security Sprint 3 - Keine UI- oder Startup-Projektion

Security Sprint 3 ergänzt keine UI-Felder, Aktionen, Anzeigen oder
Einstellungswerte. Es gibt keine sichtbare Engine-Auswahl, keinen
Verschlüsselungsstatus und keine Schlüsselabfrage. Login, Passwortwechsel,
Recovery, Support-Reset, Backup/Restore und Startreihenfolge bleiben
unverändert und rufen den SQLCipher-Provider nicht auf.

## Security Sprint 2 - Keine UI-Projektion

Security Sprint 2 fügt keine UI-Felder, Aktionen oder sichtbaren Statuswerte
hinzu. DMK, Key-ID, Fingerprint, Envelope und Plattformstore-Zustand werden
nicht projiziert. Die bestehende Passwortwechsel-UI bleibt unverändert und
führt keine DMK-Operation aus.

## Sprint 0.2S.1 - Jenaplan Support-Assistent

| UI-Feld/Aktion | Quelle/Command | Persistenz | Regel |
|---|---|---|---|
| Anwendung | statischer Produkttext `Jenaplan-Kompetenzmanager` | Nein | keine Produkterkennung oder Runtime-Suche |
| Benutzername | unverändertes Requestformat 1 | Nein | `Nicht in dieser Anfrage enthalten`; kein Nachladen |
| Gerätename / Installationsname | bewusste flüchtige Supporteingabe | Nein | ersetzt niemals die Installations-ID |
| Installationskennung | `SupportResetRequest.installation_id` | Nein | nur gekürzt sichtbar |
| Anfrage- und Ablaufzeit | geprüfter `SupportResetRequest` | Nein | lokale verständliche Anzeige, Prüfung in UTC |
| Status | Requestformat und Zeitprüfung | Nein | nur vollständig gültige Anfrage gelangt zur Erzeugung |
| Anfragecode | `support_request_reference` aus Installationsname und Request-ID | Nein | nur telefonische Zuordnung, keine Sicherheitsbindung |
| Supportschlüssel / Status | `PRODUCT_SUPPORT_KEY_REGISTRY` | Nein | `support-2026-b`, `aktiv`; kein Testkey-Fallback |
| Fingerprint | SHA-256 des registrierten Public Keys | Nein | gekürzt sichtbar |
| privater Schlüssel | bewusste Dateiauswahl | Nein | extern, verschlüsselt, `600`, kein Symlink |
| Passphrase | temporäres verdecktes Eingabefeld | Nein | nie Log, Audit, Zwischenablage oder Argument |
| Gültigkeit | feste Auswahl 15/30/60/120 Minuten | Nein | nie länger als Request oder zwei Stunden |
| Reset-Code erzeugen | `SupportAssistantApplicationService.generate_reset_code` | Audit ohne Token | verwendet unveränderten Generator und Key-ID |
| Kopieren | flüchtiger Token | Zwischenablage nur nach Klick | keine automatische Übertragung |
| Datei speichern | flüchtiger Token | bewusste `.jkmresettoken`, exklusiv `600` | keine automatische Ablage, kein Überschreiben |

Nonce, interne Payload, Hashwerte außer dem gekürzten öffentlichen
Key-Fingerprint, vollständige Installations-/Nutzer-ID und technische
Fehlerdetails werden nicht angezeigt.

## Sprint 0.2U.2 - Updates und Pilot-Testdatenhandoff

| UI-Feld/Aktion | Quelle/Command | Persistenz | Regel |
|---|---|---|---|
| Aktuelle Version / Build | `src.version` | Nein | exakt Bundle-/Release-Metadaten |
| Kanal `Pilot` | `UpdateChannel.PILOT` | Nein | fest, nicht durch Lehrkraft editierbar |
| Letzte Prüfung | Sparkle `lastUpdateCheckDate` | Sparkle-Systemzustand | keine lokale ID oder Telemetrie |
| Nach Updates suchen | `UpdateApplicationService.check_for_updates` -> `MacOSSparkleAdapter` | Nein | nur bewusster Start; Standard-Sparkle-Fenster übernimmt Release-Hinweise und Bestätigung |
| Pilottest mit Beispieldaten fortsetzen | Pilot-Build-Info | nur bestehender Onboarding-Fortschritt | im Stable-Kanal unsichtbar |
| Testdaten jetzt einspielen | `AppShell` -> vorhandene Datensicherungsseite und `prepare_restore` | Nein | nur Dateiauswahl öffnen; keine Suche, Vorauswahl oder Bestätigung |
| Anleitung öffnen | gebündelte Erste-Schritte-PDF | Nein | keine Netzwerk- oder Fachdatenquelle |

Feed, Signatur und Installation besitzen keine View-Ownership. Die UI erhält
nur strukturierte Zustände und öffnet das native Sparkle-Fenster.

## Sprint 0.2B.6 - Externes Support-Werkzeug

| Prompt/Aktion | Quelle/Command | Persistenz | Regel |
|---|---|---|---|
| Anfragepfad oder Anfrageblock | bewusste Supporteingabe -> `SupportResetTokenCodec.decode_request` | Nein | keine automatische Suche; striktes Format und Größenlimit |
| technische Anfrageübersicht | `SupportResetRequest` | Nein | Anfrage-ID vollständig, Installation/Konto gekürzt, Zeiten; keine Nonce- oder Fachdatenanzeige |
| Gerätebestätigung | exakte Eingabe `JA` | Nein | ohne Bestätigung kein Schlüsselzugriff und kein Token |
| privater Schlüsselpfad | bewusste Supporteingabe | Nein | verschlüsseltes PKCS#8, `600`, kein Symlink, keine Suche |
| öffentliche Schlüsselbeschreibung | bewusste Supporteingabe | Nein | `key_id`, Algorithmus, Status, Public-Key und Fingerprint werden strikt gebunden |
| Passphrase | Python `getpass` | Nein | unsichtbar, höchstens drei Versuche, nie Argument/Umgebungsvariable/Log |
| Gültigkeitsdauer | feste Auswahl 15/30/60/120 | Nein | Standard 30, nie länger als zwei Stunden |
| Tokenziel | bewusste Pfadeingabe -> exklusive Datei | `.jkmresettoken` mit `600` | kein Überschreiben; keine automatische Ablage |
| Token zusätzlich anzeigen | separate exakte Eingabe `JA` | nur Terminal | Warnhinweis; standardmäßig nicht anzeigen |
| Abschluss | Payload plus öffentliche Beschreibung | Nein | nur Zielpfad, Ablauf, `key_id`, Fingerprint |

Die Support-Terminalansicht ist keine App-View und kommt nicht in App, DMG oder
Laura-Paket. Die Lehrkraft-UI und ihr bestehendes Mapping bleiben unverändert.

## Sprint 0.2R - Release-Dokumentation

Version `0.2.0` fügt keine UI-Felder hinzu. Dokumentation und Screenshots bilden
nur bereits registrierte UI-Projektionen ab. Die Produktversion stammt aus
`src/version.py`; Signierungs-, Notarisierungs-, Produktivschlüssel- und reale
Hardware-Prüfstände erscheinen ausschließlich in Release-Hinweisen und
Build-Inventar, nicht als neuer persistenter UI-State.

Die Sicherheitsgrenze wird nutzernah als `Die App-Sperre ist keine
Verschlüsselung der Datenbank, Dokumente oder Backups.` wiedergegeben. Eine
fehlende, widerrufene oder abgelaufene Support-Key-Freigabe darf nie als
erfolgreiches Reset-Ergebnis projiziert werden.

## Sprint 0.2B.5 - Support-Reset-UI

| UI-Feld/Aktion | Quelle/Command | Persistenz | Regel |
|---|---|---|---|
| Weitere Wiederherstellungsmöglichkeiten | statische Auth-Gate-Navigation | Nein | nur Login/Recovery, keine Fachhauptnavigation |
| Reset-Anfrage erstellen | `SupportResetService.create_request` | bestehender Security Store v3 | genau eine aktive Anfrage; keine Fachdaten |
| Installations-/Nutzer-/Anfrage-ID und Ablauf | datensparsame Projektion aus `SupportResetRequest` | nur Security Store / flüchtige Anzeige | IDs gekürzt angezeigt, vollständige Kopie nur bewusst |
| Technische Anfrage kopieren | kanonische Requestbytes | Zwischenablage nur nach Klick | keine automatische Zwischenablage |
| Anfrage exportieren | kanonische Requestbytes | bewusste `.jkmresetrequest`-Datei | kein automatischer Pfad oder Export |
| Reset-Code | temporäre Texteingabe / bewusster `.jkmresettoken`-Import | Nein | Größenlimit, keine Logs/Preferences, nach Fehler/Abschluss löschen |
| Reset-Code prüfen | `SupportResetService.verify_token` | Nein | vollständige Prüfung; generische Fehlermeldung; kein Konsum |
| Support-Reset-Freigabe | `DEFAULT_SUPPORT_KEY_REGISTRY` mit aktivem `support-2026-b` | Nein | ab `0.2.2` produktiv prüfbar; kein Testkey-Fallback und keine Schlüsseldetails in der normalen UI |
| Reset-Vorschau | `SupportResetVerificationResult` plus statische Folgen | Nein | keine Signaturdetails oder Fachdaten |
| Sicherheitsbackup erstellen und Passwort zurücksetzen | `VerifiedSecurityBackupAdapter` -> `SupportResetService.execute` | normales `.jkmbackup` plus atomarer Security-Commit | zweite bewusste Bestätigung, keine Mehrfachauslösung |
| Fortschritt/Fehler | Workerphase und datensparsame Ergebnisprojektion | Nein | kein Prozentwert, kein Exception-/Token-/Pfadtext |

Nach Erfolg beendet der Desktop die Sitzung und App. Der nächste Start projiziert
den bestehenden `password_reset_pending`-Flow; `display_name` und Onboardingstatus
bleiben aus AppPreferences erhalten.

## Sprint 0.2B.4a - Geräteanmeldung und Touch ID

| UI-Feld/Aktion | Quelle/Command | Rolle | Persistenz | Regeln |
|---|---|---|---|---|
| Auf diesem Gerät angemeldet bleiben | `DeviceCredentialService.status` / Aktivierung nach Passwort | Anzeige/Schreibaktion | Secret nur Keychain, Hash/Metadaten nur Security Store | nie automatisch; Sperre bleibt aktiv; auf unsupported Plattform nicht angeboten |
| Hinweis zur Sperre | konstanter Produkttext | Anzeige | Nein | `Die App wird weiterhin nach Inaktivität oder Ruhezustand gesperrt.` |
| Touch ID zum Entsperren verwenden | `LocalDeviceAuthenticator.availability` plus aktives Credential und aktuelle Passwortbestätigung | Anzeige/optionale Aktion | nur boolesche Bedienpräferenz in AppPreferences, kein biometrisches Datum | nur sichtbar bei unterstütztem Mac; Aktivierung erst nach Passwortbestätigung; Passwort bleibt verfügbar |
| Touch-ID-Status | strukturierte Verfügbarkeitsprojektion | Anzeige | Nein | `verfügbar`, `nicht eingerichtet`, `nicht verfügbar`, `aktiviert` |
| Mit Touch ID entsperren | LocalAuth-Ergebnis -> Credential-Verifikation | temporäre Aktion | Nein | kein Dialogloop; Abbruch/Fehler lassen Passwortfeld verfügbar |
| Gespeicherte Anmeldung widerrufen | `DeviceCredentialService.disable` | Schreibaktion | Store zuerst revoked, Keychain best effort gelöscht | nicht löschbares Secret bleibt wegen Store/Epoch unwirksam |
| Passwort-Fallback | bestehender Passwortservice | Eingabe/Aktion | nur bestehender Argon2id-Hash | immer sichtbar und verfügbar |

Es gibt kein UI-Feld für Secret, Hash, Salt, `credential_id`, Security-Epoch,
Keychain-Account oder biometrische Details. `app-preferences.json` bleibt ohne
Credentialdaten; AppPreferences darf ausschließlich die boolesche
Touch-ID-Bedienpräferenz speichern. Aktivierungs- und Verfügbarkeitsstatus werden
weiterhin kanonisch aus Credential und Plattformadapter abgeleitet.

## Sprint 0.2B.4 - Security-Oberflaechen

| UI-Feld/Aktion | Quelle | Modus | Persistiert | Grenze |
| --- | --- | --- | --- | --- |
| Startzustand | `SecurityStartupResolver` aus Store-/Marker-Zustand und rein technischer Legacy-Erkennung | Anzeige/Navigation | Nein | kein fachlicher DB-Zugriff |
| Passwort und Bestaetigung | temporaerer Widget-State -> `SecurityApplicationService` | Eingabe | nur Argon2id-Hash im Security Store | Anzeigen/Verbergen und Einfuegen erlaubt; kein Logging/Clipboard-Autofill |
| Wie dürfen wir dich begrüßen? | temporaerer Widget-State -> `normalize_display_name` -> `AppPreferencesFile` | optionale Eingabe | `<runtime-root>/app-preferences.json`, erst nach bestaetigter Kontoaufnahme | Beispiel `Zum Beispiel Laura`; kein Einfluss auf Auth-Aktivierung; keine automatische Uebernahme aus E-Mail, Schule, OS oder Schuelerdaten |
| Recovery-Code | temporaerer Widget-State -> Recovery-Service | Eingabe | nur gesalzener Digest und Nutzungsstatus | generische Fehler, eigene Drosselung |
| Zehn neue Recovery-Codes | `EnrollmentResult`/`RecoveryPreparation` | einmalige Anzeige | Klartext nie persistiert | Sicherungsbestaetigung zwingend, druckfreundlich, keine automatische Ablage |
| Login-Sperrzeit | `LockState.remaining_seconds` | Anzeige | Drosselzustand im Security Store | keine Nutzerwahl oder fachlicher Hintergrund |
| Passwortschutz aktiv | validierter Security-Store-Zustand | Anzeige | Nein | keine vollstaendigen IDs |
| Automatische Sperrzeit | `AppPreferences` | Auswahl 5/10/15/30/60 | `app-preferences.json` | kein `Nie`, keine freie Eingabe |
| Persönliche Begrüßung | `AppPreferences.display_name` | Anzeige/Eingabe | `app-preferences.json` | optional, Unicode, maximal 80 Zeichen, nur aeussere Leerzeichen entfernt, leere Eingabe loescht; Klartext ohne HTML-Auswertung |
| Erste Schritte | `AppPreferences.onboarding_status` + `onboarding_current_step` | Navigation/Anzeige | `app-preferences.json` | lokale Orientierung nach Auth und Shell-Aufbau; kein fachlicher Assistent, keine Datenanlage |
| Erste Schritte erneut öffnen | bestehende Einstellungsübersicht -> `AppShell.open_onboarding_from_settings` | Navigation | erst bei bewusster Fortsetzung | keine neue Einstellungsunterseite; completed/dismissed werden durch bloßes Öffnen nicht zurückgesetzt |
| Passwort aendern | Security Application Service | Schreibaktion | Security Store | Epoch erhoehen, Recovery-Satz erhalten |
| Recovery-Codes neu erzeugen | zweiphasiger Recovery-Satz | Schreibaktion | Security Store | Aktivierung erst nach Bestaetigung |
| Jetzt sperren | `SecuritySessionController` | temporaere Aktion | Nein | fachliche Fenster vollstaendig unsichtbar |
| Hinweis zur App-Sperre | konstanter Produkttext | Anzeige | Nein | `Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.` plus FileVault-Hinweis |

Touch ID, Keychain, Windows Hello, `angemeldet bleiben`, Support-Reset-Token,
Cloud/E-Mail, Rollen und Verschluesselungsstatus besitzen keine UI-Felder.

Dieses Dokument beschreibt, aus welcher Datenquelle sichtbare UI-Informationen stammen.

UI-Felder duerfen nicht eingefuehrt werden, ohne ihre Datenherkunft hier zu dokumentieren.

Sprint 0.2A.2 fuehrt ausschliesslich ein injizierbares Backup-Backend ein. Sprint 0.2A.3a ergaenzt read-only Datenbank-Kompatibilitaet, Restore-Verifikation und eine rein technische, nicht sichtbare `RestorePreview`. Sprint 0.2A.3b ergaenzt ausschliesslich technisches Restore-Staging, vorbereitete V1-Kopie, Managed-File-Materialisierung, Pfad-Rebasing, Prepared-Verifikation, Cleanup und ein getrenntes Sicherheitsbackup. Sprint 0.2A.3c ergaenzt exklusiven Lock, Handoff, Worker, Journal, Live-Austausch, Rollback, Start-Recovery und Startup-Handshake ausschliesslich als technische Betriebsfunktionen. Es entstehen keine sichtbare Ansicht, keine UI-Aktion und keine neuen UI-Felder; deshalb besitzen diese Betriebsfunktionen keine Feldzuordnung. Eine spaetere Settings-, Backup- oder Restore-UI benoetigt vor ihrer Implementierung eine eigene Product-Owner- und Mapping-Freigabe.

Spalten:

- Projektionstyp: `Anzeige`, `Navigation`, `Filter`, `Eingabe`, `Auswertung`
- Schreibend: `Nein`, `Ja (ueber freigegebenen Prozess)`, `Geplant`, `Nie`
- Verantwortliche Datenquelle: Datenquelle, die fachlich fuer das Feld verantwortlich ist

## App Shell

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| App-Info | statische Produkttexte | Anzeige | Nein | keine fachliche Datenquelle | benennt App-Name, Entwickler, lokale Desktop-App, Kurzbeschreibung und Copyright; zeigt keine technische Versions-, Build-, Pfad- oder Repositoryinformation ohne freigegebene aktuelle Produktquelle |
| App-Icon | versioniertes Asset `assets/app_icon.png` | Anzeige | Nein | keine fachliche Datenquelle | sichtbares Branding in Sidebar und Info-Dialog; keine Fachlogik |
| Globale Navigation | statische `NAVIGATION_ITEMS` | Navigation | Nein | keine fachliche Datenquelle | `ARBEIT`: `Heute`, `Schüler`; `VERWALTUNG`: `Stammdaten`, `Einstellungen`; keine leeren globalen Beobachtungs-, Kompetenz- oder Berichtsziele |
| Lokale Schuelernavigation | temporaerer `StudentsWorkspace`-State | Navigation / Filter | Nein | keine fachliche Datenquelle | Segmente `Stammgruppen`, `Kurse`, `Kursverbünde`, `Alle Schüler`; Drill-down behaelt den lokalen Ursprung, fachliche IDs und bestehende Filterprojektionen |
| Visuelles Theme | freigegebene Icon-Leitlinie und Tokens aus `docs/DESIGN_SYSTEM.md` | Anzeige | Nein | keine fachliche Datenquelle | native Systemschrift, semantische Farben/Typografie/Abstaende/Radien/Elevation/Motion, zentrale Buttonrollen und SVG-Shell-Icons; keine Fachlogik |
| Shell-Feedback | bestehende Shell-Ergebnisse und UI-Zustaende | Anzeige | Nein | keine fachliche Datenquelle | nicht blockierender `Toast` fuer kurze Rueckmeldung; `InlineMessage` fuer kontextgebundene Hinweise; keine Persistenz |
| Zurück zu Erste Schritte | fluechtiger Shell-Zustand nach Onboarding-Navigation | Navigation | Nein | keine fachliche Datenquelle | nur sichtbar, wenn aus dem Onboarding zu einer bestehenden Seite navigiert wurde; normales Weiterarbeiten bleibt moeglich |

## PySide6 Erste Schritte

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Aktueller Schritt | `OnboardingController` aus `AppPreferences.onboarding_current_step` | Anzeige/Navigation | Ja, nur lokale Praeferenz | `app-preferences.json` | Schritte 1 bis 5; App-Ende oder Navigationssprung behalten den Schritt |
| Willkommen mit Namen | `AppPreferences.display_name` | Anzeige | Nein | `app-preferences.json` | optional, Plain Text, kein Security-Attribut |
| Zweck- und Datenschutzhinweis | konstanter Produkttext | Anzeige | Nein | keine fachliche Datenquelle | nennt lokale Datenhaltung und die Grenze: App-Sperre ist keine Verschluesselung |
| Status Arbeitsgrundlage | bestehende Adapter-/ViewModel-Projektionen fuer Faecher, Stundenplan und Stammdaten; Kinderstatus aus `CurrentMembershipReadSnapshot` | Anzeige | Nein | vorhandene fachliche Datenquellen, nur aggregiert | aktuelle `ENROLLED`-Mitglieder ergeben `Bereits eingerichtet`, ein fachlich leerer aktueller Bestand `Noch offen`, `CURRENT_SCHOOL_YEAR_MISSING` oder `AMBIGUOUS` `Nicht geprüft`; keine Namen, Scores, Prozentwerte, V2-Zählung oder erfundene Null |
| Zielbuttons | bestehende Shell-/Settings-Routen | Navigation | Nein | keine neue fachliche Datenquelle | navigiert nur zu vorhandenen Seiten; fehlendes Ziel zeigt ruhige Rueckmeldung |
| Weiter/Zurück | `OnboardingController` | lokale Navigation | Ja, nur lokale Praeferenz | `app-preferences.json` | Enter aktiviert Weiter beziehungsweise Abschliessen |
| Erste Schritte überspringen | Bestätigung -> `OnboardingController.dismiss` | lokale Praeferenz | Ja | `app-preferences.json` | vollständiger Buttontext; `Weiter ansehen` bleibt blaue Default-/Escape-Aktion; Enter oder Escape ueberspringen nicht unbemerkt |
| Abschließen | `OnboardingController.complete` | lokale Praeferenz/Navigation | Ja | `app-preferences.json` | danach normales Dashboard; keine automatische Sicherung oder Datenanlage |

## PySide6 Einstellungen

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Einstellungsübersicht | lokaler `SettingsScreen`-Navigationsstate + vorhandene Stundenplan-/Fach-/Backup-/Security-Projektionen | Navigation / Anzeige | Nein | keine neue fachliche Datenquelle | vier Navigationskarten plus dezente Allgemein-Aktion; Bearbeitung nur in genau einer Unterseite; erneutes Öffnen beginnt in der Übersicht |
| Datensicherungsstatus | `BackupSummaryViewModel` aus vollständig verifiziertem `.jkmbackup` | Anzeige | Nein | vorhandener Backup-Service / Runtime-Ordner `backups/` | keine Dateizeit als Vertrauensbeweis; keine Namen, Pfade oder personenbezogenen Daten |
| Restore-Vorschau | `RestorePreviewViewModel` aus vorhandener `RestorePreview` | Anzeige / bestätigte Betriebsaktion | Ja, nur technisch | vorhandener Restore-Service | nur Versionen und aggregierte Counts; Auswahl, Prüfung, Vorschau und ausdrückliche Bestätigung vor Workerstart; die Bestätigung nennt ausdrücklich, dass nicht gespeicherte Änderungen in geöffneten Arbeitsfenstern verworfen werden |
| Laufende Datensicherungsoperation | `BackupRestoreOperationsState` + `BackupRestoreProgressPhase` | temporaerer UI-Zustand | Nein | shell-eigener Operations-Controller | unbestimmter Fortschritt ohne Prozentwert; alle Backup-/Restore-Aktionen und Navigation bis zum echten Thread-Ende gesperrt; kein Cancel |
| Technischer Operationsfehler | `BackupRestoreOperationErrorInfo` | temporaere Fehlermeldung | Nein | Qt-Worker -> Controller -> Shell | UI erzeugt datensparsame Nutzerbotschaft; kein Core-Exception-Text, interner Pfad, Traceback oder fachlicher Inhalt |
| Restore-Worker-Uebernahme | `RestoreWorkerProcess` erst nach persistentem `worker_started` | temporaerer technischer Zustand | Nein | `BackupRestoreDesktopAdapter` / Restore-Journal | nur die bestaetigte Uebernahme darf den einmaligen, dialogfreien Shell-Shutdown auslösen; alle Workspace-Eventloops werden zuvor nach der ausdrücklichen Restore-Bestätigung beendet; fehlender, nicht ausfuehrbarer oder sofort fehlschlagender Worker zeigt den vorhandenen generischen Restore-Fehler und laesst die App geoeffnet |

Status: Sprint 2C wendet die gespeicherte Auswahl in Dokumentationsauswertungen an.

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Dokumentationsrelevante Faecher | SQLite `documentation_subject_settings` + SQLite `competencies.subject_id` / `subject_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `documentation_subject_settings` | Auswahl der Faecher, die fuer Dokumentations- und Auswertungslogik zaehlen; ohne gespeicherte Settings-Zeilen gelten alle aktiven Katalogfaecher; sichtbare Fachnamen kommen aus `competencies`, nicht aus der Settings-Tabelle; Hilfetext: `Diese Auswahl steuert, welche Fächer im Dokumentationsstand berücksichtigt werden. Beobachtungen bleiben immer erhalten.` |
| Wochenstundenplan | SQLite `timetable_entries` + aufgeloeste Namen aus `competencies`, `groups`, `courses`, `course_groups` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | `timetable_entries` | Wochentags-Tabs Montag bis Freitag; darunter nur der gewaehlte Tag als breite chronologische Zeilenliste; leerer Tag `Für <Wochentag> sind noch keine Stunden eingetragen.`; deaktivierte Stunden bleiben ruhig sichtbar; IDs bleiben unsichtbare technische Referenzen |
| Beginn und Ende | `timetable_entries.start_time` / `end_time` | Eingabe | Ja (ueber freigegebenen Prozess) | `timetable_entries` | `HH:MM`, Beginn strikt vor Ende; aktive Ueberschneidungen werden abgelehnt |
| Fach | `timetable_entries.subject_id` -> `competencies.subject_name` | Eingabe / Anzeige | Ja (nur ID-Referenz) | `competencies` / `timetable_entries` | Auswahl nur aus vorhandenen Fach-IDs; kein kopierter Fachname |
| Zielart und Ziel | `timetable_entries.target_type` / `target_id` -> `groups`, `courses` oder `course_groups` | Eingabe / Anzeige | Ja (nur ID-Referenz) | Stammdaten / `timetable_entries` | Ziel-ID muss zur Zielart Stammgruppe, Kurs oder Kursverbund passen |
| Raum/Ort | `timetable_entries.room` | Eingabe / Anzeige | Ja (ueber freigegebenen Prozess) | `timetable_entries` | optionaler Freitext, keine neue Raum-Stammdatenquelle |

## PySide6 Heute / technischer Screen `dashboard`

UX-Status UI Sprint 1: sichtbarer Hauptnavigationspunkt `Heute`; der technische Schluessel `dashboard` und alle Datenherkuenfte bleiben unveraendert. Die fruehere `Übersicht` ist lokal in `Schüler` integriert.

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Für diese Stunde | `TimetableDesktopAdapter.read_projection(at).current` beziehungsweise `.next` | Anzeige / Navigation | Nein | SQLite `timetable_entries` | zeigt Uhrzeit, Fach, Zielart, Ziel und optional Raum; ohne aktive laufende Stunde wird die naechste kanonische Occurrence gezeigt |
| Persönliche Tagesbegrüßung | `dashboard_greeting(at, AppPreferences.display_name)` | Anzeige | Nein | `app-preferences.json` + injizierter lokaler Zeitpunkt | vor 11 Uhr `Guten Morgen`, vor 18 Uhr `Guten Tag`, sonst `Guten Abend`; optional Name; Klartext, keine Schueler-/Stundenplandaten |
| Kein Stundenplan | `TimetableWeekViewModel.is_empty` | Anzeige / Navigation | Nein | SQLite `timetable_entries` | neutraler Leerzustand `Noch kein Stundenplan eingerichtet` mit Navigation zu Einstellungen; keine erfundenen Unterrichtsdaten |
| Heutiger Stundenplan | `TimetableDesktopAdapter.read_projection(at).today` | Anzeige / Navigation | Nein | SQLite `timetable_entries` | horizontale Timeline aus aktiven Stundenkarten; aktuelle Stunde anhand `.current` mit `JETZT` markiert, vergangene anhand des expliziten Zeitpunkts dezent; deaktivierte und geloeschte Eintraege erscheinen nicht |
| Unterrichtsziel-Navigation | `TimetableEntryViewModel.target_type` + `target_id` | Navigation | Nein | `groups`, `courses`, `course_groups` | technische ID oeffnet den passenden bestehenden Schuelerkontext; Namen sind nur Anzeige |
| Stundenplanbasierte Beobachtung | `subject_id`, `subject_label`, `target_type`, `target_id`, `target_label` der kanonischen Stunde | Navigation / Eingabe | Ja (erst im bestehenden Beobachtungsprozess) | `timetable_entries` + bestehender Beobachtungspfad | Dashboard navigiert zur Kindauswahl; danach oeffnet derselbe `NewObservationDialog` mit Fach und Unterrichtskontext fluechtig vorbelegt; keine Speicherung im Dashboard |
| Dokumentations-Heatmap | kanonische `StudentDocumentationSubjectStatus.documented_count` für die aktuellen Mitglieder aus einem refresh-lokalen `CurrentMembershipReadSnapshot` und der Dokumentationsprojektion desselben Read-Snapshots | Auswertung | Nein | `student_school_year_assignments`, V3-`students`, `competencies`, `observations`, `observation_competency_ratings`, `student_competency_confirmations`, `persistence_events`, `documentation_subject_settings` | reine Dokumentationsabdeckung `Kinder dokumentiert / Kinder der Stammgruppe`; Nenner aus zentral berechneten Counts, ein aufrufereigener transaktionskonsistenter Snapshot je Refresh, keine Abfrage je Kind oder Beobachtung und keine Python-Nachzählung; neutrale Blauabstufung, keine Ratings, Leistungsscores, Rangliste oder Entwicklungsurteile |
| Passende Kinder fuer diese Stunde | aktuelle Zielmitgliedschaft aus `CurrentMembershipReadSnapshot` mit Gruppen-, Kurs- oder Kursverbundfilter + `courses.course_name` / `courses.color_hex` + aktive `observations.date` mit eindeutigem Bezug zu `timetable_entries.subject_id` aus demselben Read-Snapshot | Anzeige / Navigation | Nein | `student_school_year_assignments`, V3-`students`, `courses`, `course_group_student_groups`, `course_group_courses`, `observations`, `observation_competency_ratings` | maximal fuenf aktuelle `ENROLLED`-Kinder; Kursverbund zentral als Schnittmenge, Kurszugehoerigkeit als dezentes `CourseBadge`; keine Fachbeobachtung zuerst, danach aelteste letzte Fachbeobachtung, kuerzlich dokumentiert und heute dokumentiert; Gleichstand alphabetisch; keine Ratings oder Kompetenzstatus |
| Beobachten beim vorgeschlagenen Kind | `DashboardSuggestedStudentViewModel.student_id` + Fach und Zielkontext der hervorgehobenen Stunde | Navigation / Eingabe | Ja (erst im bestehenden Beobachtungsprozess) | `students`, `timetable_entries`, `observations` | oeffnet direkt denselben `NewObservationDialog` fuer das Kind und belegt Fach sowie Unterrichtskontext fluechtig vor |

## Stammgruppenuebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenueberschrift | `data_groups.group_name` | Anzeige | Nein | `data_groups` | aktuelle Stammgruppe nach `group_id` |
| Schuelername auf Karte | V3-`students.first_name` + `students.last_name` für ein Mitglied des `CurrentMembershipReadSnapshot` | Anzeige | Nein | V3-`students` | Anzeige, keine technische Identitaet |
| Initialen auf Karte | V3-`students.first_name` + `students.last_name` | Anzeige | Nein | V3-`students` | abgeleitete Anzeige |
| Kurs auf Schuelerkarte | `CurrentStudentMembershipProjection.course_id` -> `courses.course_name` | Anzeige | Nein | `student_school_year_assignments` / `courses` | ausschließlich aktuelle `ENROLLED`-Zuordnung am einmalig gesetzten `as_of`-Tag; Stammgruppe wird auf Karten nicht erneut angezeigt |
| Kartenfarbe | `CurrentStudentMembershipProjection.course_id` -> `courses.color_hex` / UI-Defaultfarbe im PySide6-Scope | Anzeige | Nein | `student_school_year_assignments` / `courses` | farbliche Projektion der aktuellen Kurszuordnung, keine Schuelerfarbe und kein technischer ID-Fallback |
| Suche | V3-`students.first_name`, `students.last_name`, `display_name` aus der bereits geladenen aktuellen Projektion | Filter | Nein | V3-`students` | Namen dienen nur Suche und Anzeige; keine neue SQLite- oder Assignmentabfrage |
| Navigations-ID | V3-`students.student_id` | Navigation | Nein | V3-`students` | einzige technische Identitaet fuer Schueler |
| Neuer Schueler | keine fachliche Datenquelle | Navigation | Nein | keine | oeffnet in der Hauptanwendung den PySide-Dialog `Neuer Schüler`; historischer `dlg_neuer_schueler`-Pfad bleibt Legacy |
| Neue Beobachtung | `student_id` eines aktuellen `ENROLLED`-Mitglieds aus `CurrentMembershipReadSnapshot` | Navigation | Geplant | V3-`students` / `student_school_year_assignments` | startet spaeter zentralen Beobachtungsdialog; keine Neuauswahl aus EXITED-, unzugeordneten oder archivierten Kindern |

## Kursuebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Kursueberschrift | `data_courses.course_name` | Anzeige | Nein | `data_courses` | aktuelle Kursauswahl nach `course_id` |
| Schuelername auf Karte | V3-`students.first_name` + `students.last_name` für ein Mitglied des `CurrentMembershipReadSnapshot` | Anzeige | Nein | V3-`students` | Anzeige |
| Stammgruppe auf Karte | `CurrentStudentMembershipProjection.group_id` -> `groups.group_name` | Anzeige | Nein | `student_school_year_assignments` / `groups` | Kursuebersicht zeigt die aktuelle Stammgruppe je `ENROLLED`-Schueler |
| Kartenfarbe | `CurrentStudentMembershipProjection.course_id` -> `courses.color_hex` | Anzeige | Nein | `student_school_year_assignments` / `courses` | konsistent zur aktuellen Kurszuordnung, keine technische ID als Ersatztext |
| Suche | V3-`students.first_name`, `students.last_name`, `display_name` aus der bereits geladenen aktuellen Projektion | Filter | Nein | V3-`students` | filtert nur die geladene Projektion |
| Navigations-ID | V3-`students.student_id` | Navigation | Nein | V3-`students` | oeffnet Schuelerprofil |

## Schuelerprofil

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Profilkopf | V3-`students.student_id` | Navigation | Nein | V3-`students` | Profil wird technisch ueber `student_id` geoeffnet |
| Schuelername | V3-`students.first_name` + `students.last_name` | Anzeige | Nein | V3-`students` | Anzeige |
| Stammgruppe | `CurrentStudentMembershipProjection` aus `SchoolYearAssignmentReadSession` -> `groups.group_name` | Anzeige | Nein | `student_school_year_assignments` / `groups` | aktuelle organisatorische Zugehoerigkeit bei `ENROLLED`; `EXITED`, `NO_ASSIGNMENT` und `STUDENT_ARCHIVED` werden neutral angezeigt, `CURRENT_SCHOOL_YEAR_MISSING` und `AMBIGUOUS` blockieren |
| Kurs | `CurrentStudentMembershipProjection` aus `SchoolYearAssignmentReadSession` -> `courses.course_name` + `courses.color_hex` | Anzeige | Nein | `student_school_year_assignments` / `courses` | aktuelle Zugehoerigkeit bei `ENROLLED` als `CourseBadge`; Text bleibt sichtbar, Farbe ist weder Status noch Bewertung; keine V2- oder technische-ID-Ersatzanzeige |
| Dokumentationsring im Profilkopf | `StudentDocumentationSubjectStatus.learning_area_statuses` aus der kanonischen Dokumentationsstatusprojektion | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | zeigt Lernbereiche mit mindestens einer dokumentierten konkreten Kompetenz im Verhältnis zu allen aktiven dokumentationsrelevanten Lernbereichen; keine Prozentzahl, Leistungs- oder Ampelsemantik |
| Orientierungskarte im Arbeitsprofil | `StudentProfileDashboardViewModel.orientation_changes` aus kanonischen `StudentCompetencyStatusViewModel.evidence` und vorhandener aktueller Bestätigung | Auswertung / Navigation | Nein | `data_observations` / `data_observation_competencies` / `student_competency_confirmations` / `data_competencies` | höchstens drei konkrete Kompetenzen mit mindestens zwei realen Ereignissen und mindestens einem tatsächlichen Statuswechsel bis zum Stichtag; neueste Änderung zuerst, bei Gleichstand curriculare Reihenfolge. Jede kompakte Karte zeigt Kompetenz, Fach/Thema, `Ausgangslage`, `Aktueller dokumentierter Stand` und genau den datierten auslösenden Beleg. Die Tokens `--`, `-`, `+`, `++` bleiben immer textlich benannte pädagogische Dokumentationsstände; Pastell-Badges und Pfeil dienen nur der Orientierung. Die gesamte Karte navigiert bei Beobachtungsbeleg zur bestehenden Beobachtung, sonst zur bestehenden Kompetenzansicht; historische Referenz nur als ruhiges Badge. Keine Scores, Prozentwerte, Noten, Rankings, Mittelwerte, Lerngeschwindigkeit, Interpolation oder automatische Trendinterpretation |
| Kompetenzkarte im Arbeitsprofil | `StudentProfileDashboardViewModel.documentation_summary`, `.confirmed_documented_count` und `.observed_only_count` | Auswertung / Navigation | Nein | kanonische Kompetenzstatus- und Dokumentationsstatusprojektion | zeigt Dokumentationsumfang und Herkunft; Bestätigung und Beobachtung bleiben getrennt, alle Counts sind Dokumentations- und keine Leistungswerte; öffnet nur das bestehende Kompetenz-Cockpit |
| Noch nicht dokumentiert im Arbeitsprofil | `StudentProfileDashboardViewModel.undocumented_count` und `.undocumented_subjects` | Auswertung / Navigation | Nein | kanonische Dokumentationsstatusprojektion | neutraler Umfangshinweis nach curricularer Fachreihenfolge; fehlende Dokumentation ist kein negativer Status und öffnet nur das bestehende Kompetenz-Cockpit |
| Profil-Reiter | bestehende Profil-ViewModels | Navigation / Struktur | Nein | keine neue Datenquelle | `Überblick` ist Startreiter; `Beobachtungen`, `Kompetenzen`, `Bericht` und `Dateien` enthalten die bestehenden Detailbereiche ohne neue Persistenz; ein zentrales `SegmentedControl` steuert den weiterhin zustands- und scrollsicher verantwortlichen `QTabWidget` |
| Beobachtungsverlauf | `data_observations` + `data_observation_competencies` | Anzeige | Nein | `data_observations` | kompakte aufklappbare Karten, neueste Beobachtungen oben; ohne aktive Filter werden drei neueste Beobachtungen gezeigt und bei Bedarf erweitert; Kompaktansicht zeigt Datum, Fachlabel, Kontext, Notizvorschau und Kompetenzanzahl; Detailansicht zeigt volle Notiz und Kompetenzbewertungen; Fachlabel aus Kompetenzfaechern, bei mehreren Faechern `Fächerübergreifend` |
| Beobachtungsfilter Fach | `ObservationListItem.subject_display_name` | Filter | Nein | `data_observations` | filtert nur den Beobachtungsverlauf; Optionen `Alle`, vorhandene Fachlabels und `Fächerübergreifend`, wenn vorhanden |
| Beobachtungsfilter Bewertung | `ObservationRatingViewModel.rating` | Filter | Nein | `data_observation_competencies` | filtert nur den Beobachtungsverlauf nach Beobachtungen mit mindestens einer passenden Kompetenzbewertung |
| Beobachtungssuche | `ObservationListItem.context`, `ObservationListItem.note`, `ObservationRatingViewModel.learning_area`, `competency_group`, `competency_text` | Filter | Nein | `data_observations` / `data_observation_competencies` | lokale Textsuche auf vorhandenen ViewModel-Daten; keine SQLite-Abfrage; Sprint-3A-Mapping: `learning_area` = Kompetenzbereich, `competency_group` = Thema, `competency_text` = Kompetenz |
| Dokumentationsstatus in Schuelerlisten | Dokumentationsprojektion für die Mitglieder des `CurrentMembershipReadSnapshot` aus SQLite `competencies`, aktiven `data_observations`, `student_competency_confirmations`, `persistence_events` und `documentation_subject_settings` | Auswertung | Nein | `student_school_year_assignments` / V3-`students` / `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `persistence_events` / `documentation_subject_settings` | kompakte Summary je aktuellem `ENROLLED`-Schueler; Assignment- und Dokumentationsdaten auf derselben Connection und im selben transaktionskonsistenten Snapshot, keine Abfrage je Kind oder Beobachtung; konkrete aktive Kompetenzen zaehlen, nicht dokumentationsrelevante Faecher zaehlen nicht als offen |
| Schnellbeobachtung in Schuelerlisten | `StudentListItem.student_id` -> `NewObservationDialog` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | kompakte Zeilenaktion `Beobachten`; oeffnet bestehenden Beobachtungsdialog fuer genau diesen Schueler; Speichern laeuft ueber Adapter/Service/Repository |
| Dokumentationsstand im Schuelerprofil | SQLite `competencies` + aktive `data_observations` + `student_competency_confirmations` + `documentation_subject_settings` | Auswertung | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` / `documentation_subject_settings` | kuenftige Sprint-3-Zielregel: konkrete aktive Kompetenzen zaehlen, Anzeige darf nach Fach -> Kompetenzbereich -> Thema aggregiert bleiben, z. B. `Mathematik -> Groessen & Messen -> Zeit: 2/6 Kompetenzen beobachtet`; Standardansicht kompakt, Fachdetails per `Details anzeigen`; Soft Deletes ausgeschlossen; Bestaetigungen zaehlen als dokumentiert |
| Kompetenz-Cockpit | kanonische `StudentCompetencyStatusViewModel`-Zeilen aus `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` | Anzeige / Navigation | Nein | `data_competencies` / `data_observation_competencies` / `student_competency_confirmations` | rein lesende Hierarchie Fach -> Kompetenzbereich -> Thema -> Kompetenz; Fach-, Bereichs-, Themen- und Kompetenzkarten verwenden jeweils ihre gesamte sichtbare Flaeche sowie Enter/Leertaste fuer denselben lokalen Disclosure-State wie der vorhandene `Öffnen`-Button. Lokale Suche sowie Fach-, Dokumentations- und Klassenstufenfilter schraenken nur sichtbare aktive Karten und Zeilen ein. `Passende Kompetenzen` zeigt `stage_1_3` und `cross_stage`, `Klassenstufe 4` zeigt `stage_4` und `cross_stage`, `Alle Kompetenzen` den gesamten aktiven aktuellen Zielbestand. `Dokumentiert` umfasst aktive Beobachtung oder Bestaetigung, `Noch nicht dokumentiert` weder, `Beobachtet, noch nicht bestätigt` nutzt `observed_unconfirmed`, `Bestätigter Stand` umfasst `confirmed` und `newer_observations`, der letzte Filter nur `newer_observations`. Fach- und Kompetenzbereich zeigen weiterhin dokumentiert/gesamt und neutrale Fortschrittsbalken aus dem vollstaendigen aktiven Zielbestand; alle Ebenen starten geschlossen und behalten ihren Aufklappzustand lokal. Historische Zeilen bleiben separat unter `Historisch dokumentiert` und werden nicht gefiltert. Kompetenzdetails zeigen den kanonischen Dokumentationszustand, bei vorhandener Bestätigung deren Bewertung, Datum und Notiz, einen klar getrennten Vorschlag aus Beobachtungen sowie aktive eindeutige Nachweise neueste zuerst. Nachweise verwenden die bestehende `observation_id` zur Navigation in den vorhandenen Profilreiter und zum bestehenden Bearbeitungspfad; keine Statusberechnung oder zusätzliche Datenabfrage im Screen |
| Undokumentierte Kompetenzen im Cockpit | kanonische Sprint-6B-Zeilen mit `documentation_state = undocumented` | Anzeige | Nein | `data_competencies` | nicht als globale Liste; nur innerhalb eines manuell geöffneten Themas sichtbar; historisch referenzierte Kompetenzen werden nicht vermischt |
| Bestaetigter Kompetenzstand | `student_competency_confirmations.confirmed_rating` nach `student_id` + `competency_id` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `student_competency_confirmations` | paedagogische Entscheidung der Lehrkraft; ueberschreibt keine Beobachtungen und aendert den Vorschlag nicht automatisch |
| Berichtsvorschau | bestaetigter Kompetenzstand oder berechneter Vorschlag + aktive `data_observations` | Auswertung | Nein | `data_observation_competencies` / `student_competency_confirmations` / `data_observations` | strukturierte Berichtsvorbereitung nach Fach; zeigt den aktuellen Kompetenzstand je relevanter Kompetenz mit Quelle, bevorzugt bestaetigte Staende vor berechneten Vorschlaegen; Entwicklung wird getrennt aus chronologischen aktiven Beobachtungen abgeleitet und formuliert Einzelbeobachtung, stabile Verlaeufe, positive Entwicklung, Rueckschritt oder wechselnde Beobachtungslage; Soft Deletes ausgeschlossen; echte Beobachtungen und bestaetigte Kompetenzstaende bleiben sichtbar, auch wenn ein Fach nicht dokumentationsrelevant ist; kann als Text kopiert oder als einfache Textdatei exportiert werden; keine KI-Textgenerierung, keine finalen Zeugnisformulierungen, keine gespeicherte Berichtsdatenhaltung |
| Dokumente & Medien | SQLite `documents` nach `student_id` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `documents` + Dateisystem `data/documents/<student_id>/` | zeigt alle aktiven Schuelerdokumente neueste oben; Dateien werden geoeffnet, wenn `file_path` vorhanden ist; Entfernen setzt `documents.active = 0` und loescht keine physische Datei; SQLite speichert keine BLOBs |
| Neue Beobachtung | `student_id` eines aktuellen `ENROLLED`-Mitglieds aus `CurrentMembershipReadSnapshot` | Navigation | Ja (ueber freigegebenen Prozess) | V3-`students` / `student_school_year_assignments` / `data_observations` | startet zentralen Beobachtungsdialog und speichert ueber Adapter/Service/Repository; der Editpfad einer bestehenden Beobachtung behält deren gespeicherte `student_id` |
| Beobachtung bearbeiten | `data_observations.observation_id` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | oeffnet bestehenden Beobachtungsdatensatz im Dialog; Speichern ersetzt die Kompetenzbewertungen atomar |
| Beobachtung loeschen | `data_observations.observation_id` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_observations` | Soft Delete ueber `observations.active = 0`; aktive Profil- und Kompetenzuebersichten blenden die Beobachtung aus |

## Legacy: Schuelerverwaltung / `dlg_neuer_schueler`

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Vorname | zukuenftig `data_students.first_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | Pflichtfeld, keine technische Identitaet |
| Nachname | zukuenftig `data_students.last_name` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | Pflichtfeld |
| Stammgruppe | Auswahl aus `data_groups.group_name`, Speichern von `data_students.group_id` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_groups` | Pflichtauswahl, keine automatische Stammgruppenanlage |
| Kurs | Auswahl aus `data_courses.course_name`, Speichern von `data_students.course_id` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_courses` | Pflichtauswahl, keine automatische Kursanlage |
| Notiz | zukuenftig `data_students.student_notes` | Eingabe | Ja (ueber freigegebenen Prozess) | `data_students` | optional |
| Dokumentliste | zukuenftig `data_media.file_ref` nach `student_id` | Anzeige | Nein | `data_media` | zeigt referenzierte Dateien, keine Einbettung |
| Dokument hinzufuegen | zukuenftig Dateiauswahl -> `data_media` | Eingabe | Geplant | `data_media` | erzeugt spaeter `media_id` und `file_ref` nach freigegebenem Prozess |

Regel:

`dlg_neuer_schueler` ist ein historischer worksheet-basierter Dialogseiten-Stand der Excel-Linie. Er ist kein Zielpfad fuer neue UI-Entwicklung, Smoke-Tests oder produktive Workflows. Der aktive Hauptpfad ist der PySide-Schuelerdialog.

## PySide6 Schuelerdialog

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Vorname | `QLineEdit` -> `StudentDesktopAdapter.save_new_student/save_existing_student` | Eingabe | Ja | V3-`students.first_name` | Pflichtfeld, keine technische Identitaet |
| Nachname | `QLineEdit` -> `StudentDesktopAdapter.save_new_student/save_existing_student` | Eingabe | Ja | V3-`students.last_name` | Pflichtfeld |
| Notiz | `QTextEdit` -> `StudentDesktopAdapter.save_new_student/save_existing_student` | Eingabe | Ja | V3-`students.notes` | optional; Stammdatenwrite verändert keine Membership |
| aktuelles Schuljahr | `StudentDesktopAdapter.current_school_year()` | Anzeige | Nein | `school_years` | bei Anlage eindeutig erforderlich; keine Seed-, Label- oder Systemdatumsannahme |
| Stammgruppe bei Anlage | aktive Gruppen aus SQLite `groups` | Eingabe | Ja | initiales `student_school_year_assignments.group_id` | Dropdown, kein Freitext; gemeinsam mit dem Schüler atomar gespeichert |
| Kurs bei Anlage | aktive Kurse aus SQLite `courses` | Eingabe | Ja | initiales `student_school_year_assignments.course_id` | Dropdown, kein Freitext; Kurs benötigt gültige `year_level` |
| aktuelle Zuordnung beim Bearbeiten | `CurrentStudentMembershipProjection` | Anzeige | Nein | `student_school_year_assignments` | nicht über `save_existing_student` änderbar |
| Zuordnung ändern | `StudentMembershipChangeDialog` | Eingabe / Vorschau | Ja | `student_school_year_assignments` | expliziter Stichtag und bewusste Bestätigung; eigener Einzelkind-Lifecycle |
| Austritt | `StudentExitDialog` | Eingabe / Bestätigung | Ja | `student_school_year_assignments` | eigener Lifecycle; keine Archivierung |
| Archivieren | getrennte Aktion | Eingabe / Bestätigung | Ja | V3-`students` | bei aktueller Einschreibung blockiert; keine Assignmentmutation |

Regel:

Der PySide-Schuelerdialog ist der aktive Final-V3-Eingabepfad. Er sammelt
Eingaben, validiert UI-nah und nutzt den Desktop Adapter sowie getrennte
Application-/Domain-/Repository-Lifecycles. Qt Widgets schreiben nicht direkt
in SQLite. Schülerstammdaten und Membership werden nicht über ein
gemeinsames generisches Update verändert.

## PySide6 Schueleruebersicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Name | `StudentListItem.display_name` aus V3-`students.first_name` + `students.last_name` für ein Mitglied des `CurrentMembershipReadSnapshot` | Anzeige | Nein | V3-`students` | Anzeige, keine technische Identitaet; aktuelle Liste enthält ausschließlich aktive, nicht archivierte `ENROLLED`-Mitglieder |
| Kursbadge | `CurrentStudentMembershipProjection.course_name` + `.course_color_hex` | Anzeige | Nein | `student_school_year_assignments` / SQLite `courses` | dezentes `CourseBadge` in eigener Kurs-Spalte; Kursname bleibt sichtbar, keine technische ID, Zeilenfaerbung und keine Status-, Leistungs- oder Entwicklungssemantik |
| Sortierung | aktuelle Mitglieder aus `CurrentMembershipReadSnapshot` + `sort_student_list()` | Anzeige | Nein | `student_school_year_assignments`, V3-`students`, `courses` | zuerst Kursreihenfolge aus Stammdaten, dann alphabetisch nach Schuelername; keine Python-Membershipfilterung und keine Zuordnungsabfrage je Kind |
| aktiver Filterhinweis | Shell-Filterstate aus Stammgruppe, Kurs oder Kursverbund/Kurs | Anzeige | Nein | keine fachliche Datenquelle | `FilterBar` zeigt den aktiven Kontext als `FilterChip`; Reset erscheint nur bei gefilterter Liste und kehrt zur lokalen Auswahl zurueck; keine Speicherung |
| Zurueck zur Auswahl | temporaerer Shell- und `StudentsWorkspace`-State | Navigation | Nein | keine fachliche Datenquelle | erscheint in gefilterten Stammgruppen-/Kurs-/Kursverbund-Schuelerlisten, setzt den Filter zurueck und kehrt lokal zum ausloesenden Segment zurueck |
| Profil oeffnen | `StudentListItem.student_id` | Navigation | Nein | V3-`students` | einfacher Klick auf eine Nicht-Aktionszelle, Enter oder die sekundäre Zeilenaktion `Profil öffnen` navigiert genau einmal; eingebettete Aktionen bleiben davon getrennt; Namen bleiben reine Anzeige |
| Schnellbeobachtung | `StudentListItem.student_id` -> `NewObservationDialog` | Navigation / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `observations` / `observation_competency_ratings` | kompakte Zeilenaktion; nutzt denselben Beobachtungsdialog wie das Schuelerprofil und aktualisiert Liste und Dokumentationsstatus nach Speichern |

Regel: Die Schueleruebersicht liest die aktuelle Mitgliedermenge über den
`CurrentMembershipReadSnapshot` aus einer
`SchoolYearAssignmentReadSession`. `EXITED`, `NO_ASSIGNMENT` und archivierte
Schüler erscheinen nicht. Fehlendes current-Schuljahr oder `AMBIGUOUS`
blockiert die fachliche Ansicht und wird nicht als leere Liste dargestellt.
Ein fachlich leerer aktueller Bestand zeigt die leere Liste und erzeugt keine
Demo-Schueler.

## Lokale Schuelerprojektionen `Stammgruppen`, `Kurse` und `Kursverbünde`

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenliste | `MasterDataViewModel.groups` aus SQLite `groups` | Anzeige | Nein | `data_groups` / SQLite `groups` | zeigt alle persistent aktiven Stammgruppen |
| Schueleranzahl je Stammgruppe | zentral berechneter Gruppen-Count aus `CurrentMembershipReadSnapshot` | Anzeige | Nein | `student_school_year_assignments` / V3-`students` | nur aktuelle aktive, nicht archivierte `ENROLLED`-Mitglieder; keine Python-Nachzählung; `CURRENT_SCHOOL_YEAR_MISSING` oder `AMBIGUOUS` blockiert |
| Direkte Kursliste | `MasterDataViewModel.courses` aus SQLite `courses` | Anzeige / Filter | Nein | `data_courses` / SQLite `courses` | zeigt persistente aktive Kurse in vorhandener Stammdatenreihenfolge und uebergibt `course_id` an die bestehende Schuelerprojektion |
| Kursverbund | `MasterDataViewModel.course_groups` aus SQLite `course_groups` + Relationen | Anzeige / Filter | Nein | SQLite `course_groups`, `course_group_student_groups`, `course_group_courses` | definiert, welche Stammgruppen gemeinsam Mathe-/Deutsch-Kurse bilden |
| Kursliste im Kursverbund | `CourseGroupViewModel.selected_course_ids` -> `MasterDataViewModel.courses` | Anzeige / Filter | Nein | `data_courses` | Kursuebersicht ist kursverbundbezogen, nicht global ueber alle Stammgruppen |
| Kursmarker | `MasterDataItemViewModel.color_hex` | Anzeige | Nein | `data_courses` | nur kleiner Marker, keine Zeilenfaerbung |
| Kursverbund-Kursfilter | `course_id` + `course_group_id` gegen `CurrentMembershipReadSnapshot` | Filter | Nein | `student_school_year_assignments`, `course_group_student_groups`, `course_group_courses` | zentrale Schnittmenge der registrierten Stammgruppen und Kurse des Kursverbunds mit aktuellen `ENROLLED`-Assignments; kein Python- oder Widgetfilter auf Membershipintervallen |

Regel: Alle drei Projektionen werden innerhalb von `StudentsWorkspace`
angezeigt und sind keine eigenen globalen Navigationsziele. Sie lesen aktuelle
Mitgliedschaften und Counts ausschließlich aus demselben
`CurrentMembershipReadSnapshot`; der Workspace erzeugt keine fachliche
Datenquelle, berechnet keine Membership und besitzt keinen Schreibprozess.

## PySide6 Stammdaten

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Stammgruppenliste | SQLite `groups.group_name` ueber `MasterDataDesktopAdapter` | Anzeige | Nein | SQLite `groups` / `data_groups` | Stammgruppen sind eigenstaendige Stammdaten |
| Kursliste | SQLite `courses.course_name` und `courses.year_level` ueber `MasterDataDesktopAdapter` | Anzeige | Nein | SQLite `courses` / `data_courses` | Kurse sind eigenstaendige Stammdaten; Kursstufe wird als `Stufe 1`, `Stufe 2` oder `Stufe 3` angezeigt |
| Kursfarbe | SQLite `courses.color_name` + `courses.color_hex` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `courses` / `data_courses` | persistenter Farbwert am Kurs; Schuelerfarbe wird daraus abgeleitet |
| Kursverbund | `MasterDataViewModel.course_groups` aus SQLite `course_groups` | Anzeige / Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` | definiert Name, ausgewaehlte Stammgruppen und ausgewaehlte Kurse |
| Neuer Kursverbund | `CourseGroupDialog` -> `MasterDataDesktopAdapter.add_course_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` + Relationen | nutzt Name, Stammgruppen-Checkboxen und Kurs-Checkboxen; doppelte Namen werden abgefangen |
| Kursverbund bearbeiten | `CourseGroupDialog` -> `MasterDataDesktopAdapter.update_course_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `course_groups` + Relationen | Checkbox-Auswahl fuer Stammgruppen und Kurse; Kursfilter bleibt Kurs plus Stammgruppen des Kursverbunds |
| Neue Stammgruppe | `MasterDataDesktopAdapter.add_group()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `groups` / `data_groups` | erzeugt persistente Stammgruppe, keine automatische Schuelerzuordnung |
| Neuer Kurs | `MasterDataDesktopAdapter.add_course()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `courses` / `data_courses` | erzeugt persistenten Kurs inklusive Kursfarbe und bewusst gewählter Pflicht-`year_level`; mehrere Kurse derselben Stufe zulässig |
| Bearbeiten/Deaktivieren | `MasterDataDesktopAdapter.rename_*()` -> `SQLiteMasterDataRepository` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `groups` / `courses` | IDs bleiben maßgeblich; keine Schülerumbuchung. Deaktivierung benötigt einen expliziten Stichtag und wird bei aktuellen oder zukünftigen `enrolled`-Referenzen blockiert; historische Referenzen bleiben lesbar |

## Kompetenzansicht

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Kompetenzname | SQLite `competencies.label` / `competencies.description`, Katalog `competency_label` / `competency_text` | Anzeige | Nein | `data_competencies` | technische Identitaet ist `competency_id`; `label` ist Kurzlabel aus `competency_label`, `description` die konkrete Kompetenz |
| Fach / Kompetenzbereich / Thema | `competencies.subject_id` / `subject_name`, `learning_area`, `competency_group` | Anzeige | Nein | `data_competencies` | fachliche Struktur: Fach -> Kompetenzbereich -> Thema -> Kompetenz |
| Beobachtungen zur Kompetenz | `data_observation_competencies` -> `data_observations` | Anzeige | Nein | `data_observations` | keine doppelte Beobachtungsdatenhaltung |
| Kompetenzverlauf | `data_observation_competencies.rating` + `data_observations.date` | Auswertung | Nein | `data_observation_competencies` | historisierte Projektion |
| Navigations-ID | `data_competencies.competency_id` | Navigation | Nein | `data_competencies` | oeffnet Kompetenzansicht |

## Beobachtungsdialog

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| ausgewaehlter Schueler | neue Beobachtung: `student_id` aus dem aktuellen `CurrentMembershipReadSnapshot`; Bearbeitung: gespeicherte `observations.student_id` -> V3-`students` | Anzeige | Nein | V3-`students` / `student_school_year_assignments` / `observations` | Namen werden nicht als technische Identitaet verwendet; beim Edit bleibt der bestehende Schülerbezug erhalten |
| Fachauswahl | SQLite `competencies.subject_id` / `subject_name` + `documentation_subject_settings` | Eingabe | Nein | Kompetenzverwaltung / Lehrplanpflege + `documentation_subject_settings` | neue Beobachtungen bieten nur dokumentationsrelevante aktive Faecher an; App-Anzeigename `EPU`, kein App-Fach `Sachunterricht`; bei Bearbeitung bleibt das gespeicherte Fach sichtbar, auch wenn es inzwischen nicht dokumentationsrelevant ist |
| Kompetenzauswahl | SQLite `competencies`, befuellt aus `data/curriculum_catalog_v1.csv` | Eingabe | Ja | `data_observation_competencies` | Drei-Zonen-Dialog mit separat scrollbarer Auswahl und separat scrollbarem Katalog; die Adapterprojektion traegt das vorhandene `learning_stage` fuer die lokalen Ansichten `Passende Kompetenzen`, `Klassenstufe 4` und `Alle Kompetenzen`. Neue Beobachtungen bieten nur `catalog_status = current` und `active = 1` an; jede Kompetenz hat `competency_id`, Fach, Kompetenzbereich, Thema, konkrete Kompetenz und lesbares Kurzlabel; ausgewaehlte Kompetenzbewertungen koennen aus mehreren Faechern stammen; beim Bearbeiten bleiben bereits bewertete `legacy`- oder inaktive Kompetenzen mit historischem Text sichtbar, bewertbar und entfernbar. Suche, Filter und Collapse veraendern weder Auswahl noch Einzelbewertung |
| Schnellauswahl | aktive SQLite `observations` + `observation_competency_ratings` -> aktive `current`-Zeilen aus `competencies` | Anzeige / Eingabe | Nein | `observations` / `observation_competency_ratings` / `competencies` | Adapterprojektion je Schueler und aktuell gewaehltem Fach: hoechstens vier eindeutige Kompetenzen, neueste zuerst; Legacy- und inaktive Kompetenzen ausgeschlossen; ohne Eintraege oder bei aktivem Suchtext ausgeblendet; Klick fuegt nur zur bestehenden Auswahl hinzu und speichert nichts eigenstaendig |
| Beobachtungsdatum | SQLite `observations.date` | Eingabe | Ja | `observations` | Datum gehoert zur Beobachtung |
| Beobachtungsnotiz | SQLite `observations.note` | Eingabe | Ja | `observations` | Schreiben ueber Adapter, Command, Service und Repository |
| Schnellbeobachtung | bewusste Dialogeingabe; beim Bearbeiten aktive SQLite-`observations`-Zeile mit nichtleerer `note` und ohne `observation_competency_ratings` | Eingabe / Anzeige | Ja (ueber bestehenden Beobachtungsprozess) | `observations` / `observation_competency_ratings` | erlaubt Speichern ohne Kompetenz nur bei aktivierter Checkbox und nichtleerer Notiz; deaktiviert den Kompetenzbereich ohne Auswahl zu loeschen; im Verlauf dezent gekennzeichnet |
| Beobachtungskontext | SQLite `observations.context` | Eingabe | Ja | `observations` | Kontext gehoert zur Beobachtung |
| Kompetenzzuordnung | SQLite `observation_competency_ratings` | Eingabe | Ja | `observation_competency_ratings` | n:m-Zuordnung; vier direkt anklickbare Bewertungs-Chips schreiben weiterhin genau einen `rating`-Wert je konkreter `competency_id`; `offen` wird nicht gespeichert, sondern bedeutet keine Zuordnungszeile |
| Dokumente und Medien | Dateiauswahl -> `StudentDesktopAdapter` -> SQLite `documents` nach `student_id` und optional `observation_id` | Eingabe | Ja (ueber freigegebenen Prozess) | SQLite `documents` + Dateisystem `data/documents/<student_id>/` | Datei wird in den App-Datenordner kopiert; Beobachtungsanhaenge tragen zusaetzlich `observation_id`; die ruhige Dateizeile zeigt Dateiname, Typ und Entfernen-Aktion. Entfernen setzt `documents.active = 0`; keine Datei-BLOBs |

## Berichte und Dashboard

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Schuelerinformationen | V3-`students` plus datierte Assignmentauflösung aus `AssignmentReferenceRequest` und sichtbare `groups` / `courses` | Anzeige | Nein | V3-`students` / `student_school_year_assignments` / `groups` / `courses` | Bericht zeigt Stammgruppe und Kurs am `period_end`; LEG zeigt beide am `conference_date` und bleibt ohne Gesprächsdatum ausdrücklich „Zuordnung noch nicht aufgelöst“; Beobachtung verwendet `observations.date`; freies Dokument ohne Referenzdatum bleibt neutral; keine V2-, current- oder Last-known-Ersatzzuordnung |
| Beobachtungsbasis | `data_observations` | Auswertung | Nie | `data_observations` | Beobachtung ist Source of Truth |
| Kompetenzdaten | `data_observation_competencies` + `data_competencies` | Auswertung | Nie | `data_observation_competencies` | abgeleitete Auswertung |
| bestehende Berichtsvorschau im Schuelerprofil | `student_competency_confirmations`, berechnete Kompetenzvorschlaege und aktive Beobachtungen | Auswertung | Nie | SQLite / `data_observations` | bestehende vorbereitende Struktur, kein gespeicherter Bericht und keine KI-Textgenerierung |
| Berichtentwurfswahl | `StudentDesktopAdapter.list_learning_report_drafts_for_student(student_id)` -> `LearningReportDraftSelectionDialog` | Auswahl / Navigation | Nein | SQLite `report_drafts` | bei mindestens einem Entwurf bewusst bestehenden RPD nach Zeitraum und Status öffnen, neuen noch ungespeicherten Entwurf beginnen oder abbrechen; Auswahl schreibt nichts und verwechselt keine RPV mit einem Draft |
| Dokumentkontext Lernentwicklungsbericht | `LearningReportDraftViewModel` + `StudentDetailViewModel` | Anzeige / Eingabe | Ja, als Entwurf | SQLite `report_drafts`, `students`, `groups` | Berichtstyp, Zeitraum, Lehrkraft und Status werden als `draft` gespeichert; Schueler- und Gruppennamen bleiben Projektionen |
| Fach- und Kompetenzauswahl | gespeicherte Referenzen + `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` | Auswahl | Ja, als Referenzen | `report_draft_subjects`, `report_draft_competencies` + kanonische Sprint-6-Projektion | keine Kompetenztexte oder Bewertungen im Entwurf; nur aktive `current`-Kompetenzen neu auswählbar, historische Referenzen weiterhin aufloesbar |
| Beobachtungsbelege | gespeicherte `observation_id`-Referenzen + aktive Beobachtungsprojektion | Auswahl | Ja, als Referenzen | `report_draft_observations`, SQLite `observations` | Datum, Kontext und Notiz bleiben in `observations` und werden nicht in den Entwurf kopiert |
| Gesamtblick und Fachtexte | `LearningReportDraftViewModel` | Eingabe | Ja, als Entwurf | `report_drafts.overall_text`, `report_draft_subjects` | ausschliesslich manuelle Eingabe; keine KI-Formulierung, automatische Bewertung oder Zielerzeugung |
| Diagrammauswahl | `LearningReportDraftViewModel.chart_selections` | Auswahl | Ja, als Referenz | `report_draft_charts` | speichert nur Fach und Diagrammtyp; keine berechneten Diagrammdaten |
| Entwurfs-PDF-Ausgabe | vollstaendiges Draft-`ReportOutputModel` -> unveraenderter `PdfRenderer` | Ausgabe | Nein | fluechtiges Ausgabemodell | Renderer liest keine Datenbank und leitet keine Inhalte ab; kein finales Artefakt |
| Finalisierungsstatus | `LearningReportRevisionReadService.state_for_draft(report_draft_id)` -> `LearningReportRevisionStatusViewModel` | Anzeige | Nein | `learning_reports`, `learning_report_revisions` + aktueller validierter Finalisierungskandidat | zeigt `Entwurf`, `Finalisiert · Revision X` oder `Entwurf geändert`; Vergleich und Hashpruefung erfolgen zentral, nie im Widget |
| Finalisierungsbestaetigung | `ReportFinalizationService.prepare(report_draft_id)` -> `LearningReportFinalizationPreviewViewModel` | Anzeige / verpflichtender Anzeigename | Ja, ueber bestehenden Finalisierungsprozess | gespeicherter `RPD` + registrierte Finalisierungsquellen | zeigt Kind, Typ, Zeitraum, Faecher, Kompetenz-/Beobachtungsanzahl und neue Revisionsnummer; erzeugt keine Benutzer-ID |
| Revisionsprotokoll | `LearningReportRevisionStatusViewModel.history` | Anzeige | Nein | `learning_report_revisions` + unveraenderliche `learning_reports`-Identitaet | neueste Revision zuerst; Status `Aktuell` oder `Ersetzt`; ausschliesslich Aktion `Öffnen` |
| Finale Berichtrevision | `LearningReportRevisionReadService.snapshot_payload(RPV-ID)` -> `LearningReportRevisionViewModel` | schreibgeschuetzte Anzeige | Nein | ausschliesslich `learning_report_revisions.snapshot_json`, Revisionsmetadaten und `snapshot_sha256` | friert sichtbare Fachinformationen, manuelle Inhalte, Referenzprovenienz und Diagrammwerte ein; keine Live-Nachladung |
| Finales Berichts-PDF | `RPV-ID` -> `StudentDesktopAdapter.generate_learning_report_pdf` -> `GenerateLearningReportPdfCommand` -> `LearningReportPdfService` -> snapshotbasiertes `ReportOutputModel` -> `PdfRenderer` | Ausgabe / Artefaktaktion | Ja, nur Artefaktreferenz | `learning_report_revisions` + `learning_report_pdf_artifacts` + verwaltete PDF-Datei | nur Status `finalized`; keine Draft- oder Live-Daten; zeigt danach Dateiname, Erzeugungszeitpunkt und PDF-SHA-256 |
| Medienhinweise | SQLite `documents` | Anzeige | Nie | SQLite `documents` | optionale Anlagen; Berichte nutzen Medien in diesem Sprint nicht produktiv weiter |

UX-Regel Sprint 7F.2: `prototypes/learning_report_ux/` ist die verbindliche Spezifikation fuer Layout, Navigation, Arbeitsweise, Kartenstruktur, Informationshierarchie, Abstaende, Auswahlmechanismen und Vorschaukonzept. Die produktive Ansicht wechselt oben zwischen `Bericht bearbeiten` und `Berichtsvorschau`; die Bearbeitung navigiert links zwischen Dokumentkontext, den fachbezogenen Arbeitsbereichen und Abschluss. Kompetenzstaende sind anders als im isolierten Demo-Prototyp nicht editierbar, weil der Entwurf ausschliesslich `competency_id`-Referenzen speichert und die kanonische Kompetenzstatusprojektion nicht veraendert. Globale Abschluss- und interne Notizfelder werden nicht angezeigt, weil sie im unveraenderten Entwurfsmodell keine verantwortliche Datenquelle besitzen.

## Lernentwicklungsgespraech

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Gespraechsrahmen | `LearningConferenceDraftViewModel` + `StudentDetailViewModel` | Anzeige / Eingabe | Ja, als Entwurf | `learning_conference_drafts`, `students`, `groups` | Zeitraum, Gespraechsdatum und verantwortliche Lehrkraft werden gespeichert; Kind- und Stammgruppenname bleiben Live-Projektionen |
| LEG-Entwurfswahl | `StudentDesktopAdapter.list_learning_conference_drafts_for_student(student_id)` -> `LearningConferenceDraftSelectionDialog` | Auswahl / Navigation | Nein | SQLite `learning_conference_drafts` | bei mindestens einem Entwurf bewusst bestehenden LCD nach Gesprächsdatum, Zeitraum und Status öffnen, neues noch ungespeichertes eigenständiges LEG beginnen oder abbrechen; Auswahl schreibt nichts und verwechselt keine LCV mit einem Draft |
| Fachliche Bereiche | gespeicherte `subject_id`-Referenzen + kanonische Kompetenzprojektion | Auswahl | Ja, als Referenzen | `learning_conference_draft_subjects`, `competencies` | keine Fachdefinition oder Kompetenzlogik im Entwurf |
| Uebergreifende Gespraechsthemen | vier registrierte `cross_topic_key`-Werte | Auswahl | Ja, als Entwurf | `learning_conference_draft_cross_topics` | entspricht exakt Arbeitsverhalten, Sozialverhalten, Selbststaendigkeit und Lernorganisation aus dem Prototyp |
| Kompetenzen | gespeicherte `competency_id`-Referenzen + `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)` | Auswahl | Ja, als Referenzen | `learning_conference_draft_competencies` + kanonische Sprint-6-Projektion | Fach -> Kompetenzbereich -> Thema -> Kompetenz; sichtbar sind aktive kindbezogene Kompetenzbeobachtungen im vollstaendig gesetzten LEG-Zeitraum, aktuelle Bestaetigungen und bereits ausgewaehlte Draft-Referenzen; ohne vollstaendigen Zeitraum gelten alle aktiven Kompetenzbeobachtungen des Kindes; leere Zweige werden ausgeblendet; kein kopierter Text, Status oder eigene Bewertung |
| Beobachtungsbelege | gespeicherte `observation_id`-Referenzen + aktive Beobachtungsprojektion | Auswahl | Ja, als Referenzen | `learning_conference_draft_observations`, `observations` | nur Belege des Kindes neu auswaehlbar; Schnellbeobachtungen duerfen Textbeleg sein; nicht mehr aktive Referenzen bleiben kontrolliert sichtbar |
| Gespraechseinstieg, Rueckblick, Lehrkraftsicht, Staerken und Entwicklungsfelder | `LearningConferenceDraftViewModel` | Eingabe | Ja, als Entwurf | `learning_conference_drafts` | ausschliesslich manuelle Texte |
| Ziele, Unterstuetzung und Vereinbarungen | getrennte vorbereitete und gemeinsam vereinbarte Felder | Eingabe | Ja, als Entwurf | `learning_conference_drafts` | keine automatische Ziel-, Text- oder Bewertungsableitung |
| Zustaendigkeiten und naechster Ueberpruefungszeitpunkt | `LearningConferenceDraftViewModel` | Eingabe | Ja, als Entwurf | `learning_conference_drafts` | manuelle Verantwortungsangabe und optionales ISO-Datum |
| Optionale Gespraechsbilder | gespeicherter Diagrammtyp + bestehende Live-Projektionen | Auswahl / Auswertung | Ja, nur Typreferenz | `learning_conference_draft_charts` | keine gespeicherten Diagrammdaten, Scores oder Trends |
| LEG-Kontextkopf | `LearningConferencePreparationViewModel` + aktueller Widget-/Draftzustand | Anzeige | Nein | `students`, `groups`, `courses`, `learning_conference_drafts` | Kind, Stammgruppe und Kurs sind Live-Projektionen; Datum und Lehrkraft spiegeln bestehende Draftfelder; Phasen- und Speicherstatus sind fluechtiger UI-State |
| LEG-Phasenstatus | Vollstaendigkeit der bereits sichtbaren Draft-Widgets und Auswahlreferenzen | Anzeige | Nein | keine neue Datenquelle | ausschliesslich `Aktuell`, `Inhalt vorhanden` oder `Noch leer`; nicht persistiert und keine Abschlussaussage |
| LEG-Belegzusammenfassung ausserhalb Phase 5 | aktuelle lokale Kompetenz-, Beobachtungs- und Diagrammauswahl | Anzeige | Nein | bestehende Draftreferenzen + Live-Projektionen | rein lesend; `Belege ansehen` wechselt nur lokal zu Phase 5 |
| LEG-Speicherstatus und Dirty-State | Vergleich des aktuellen `LearningConferenceDraftViewModel` mit dem zuletzt geladenen beziehungsweise erfolgreich gespeicherten Widgetstand | Anzeige | Nein | keine neue Datenquelle | `Ungespeicherte Aenderungen` oder lokalisierter letzter Speicherstand; keine Autosave- oder Domainstatusbehauptung |

UX-Regel UI Sprint 6B: `docs/LEG_UX_AUDIT_AND_TARGET.md` ersetzt fuer die produktive Dialogkomposition die fruehere Zwei-Seiten-Darstellung aus Sprint 7G.2. Genau eine der sechs vorhandenen Phasen ist aktiv. `strengths_text` und `teacher_perspective_text` erscheinen als interne Vorbereitung, `child_retrospective_text` und `development_fields_text` als gemeinsam bearbeitete Inhalte, `agreed_goals_text` sichtbar in Phase 4 und die Kompetenz-/Beleg-/Diagrammauswahl in Phase 5. Alle Feldbedeutungen, Referenzen und der vollstaendige `LearningConferenceDraftViewModel`-Speicherpfad bleiben unveraendert.

### LEG-Abschluss und Revisionen

| UI-Information | Datenherkunft | Projektionstyp | Schreibend? | Verantwortliche Datenquelle | Regel |
| --- | --- | --- | --- | --- | --- |
| Abschlussaktion | gespeicherte LCD-ID | Befehl | Ja, explizit | `LearningConferenceCompletionApplicationService` | UI uebergibt ausschliesslich die ID; keine Snapshot-, Hash- oder Persistenzlogik im Widget oder ViewModel |
| Abschlussstatus | `LearningConferenceRevisionStatusViewModel` | Anzeige | Nein | `learning_conferences`, `learning_conference_revisions` + validierter Kandidat | unterscheidet noch nicht abgeschlossen, aktuell und Draft seit Abschluss geaendert |
| Abschlussfehler | `LearningConferenceCompletionErrorViewModel` aus typisiertem Domainfehler | Anzeige / Navigation | Nein | LEG-Domainvalidierung | Dialog wertet keine Fehlermeldungsstrings aus |
| Revisionshistorie | `LearningConferenceRevisionListItemViewModel` | Anzeige / Navigation | Nein | `learning_conference_revisions` | neueste zuerst; keine Bearbeiten-, Loeschen- oder Wiederherstellungsaktion |
| Finales LEG-PDF | `LearningConferencePdfArtifactViewModel` aus verifizierter `LCA` | Anzeige / Aktion | Ja, ueber freigegebenen Artefaktprozess | `learning_conference_revisions`, `learning_conference_pdf_artifacts` | Aktion nur fuer aktuelle `completed`-LCV; UI uebergibt ausschliesslich LCV-ID und besitzt keine Renderer-, Snapshot-, Hash-, Pfad- oder SQLite-Logik |
| Historische Revisionsansicht | `LearningConferenceRevisionViewModel` | schreibgeschuetzte Anzeige | Nein | verifiziertes `snapshot_json` der LCV | keine Live-Aufloesung fachlicher Werte; Integritaetspruefung vor Anzeige |

Der Abschlussbereich ist vom primaeren Draftspeichern getrennt. Solange der aktuelle Widgetstand ungespeichert ist, ist der Abschluss deaktiviert. Nach einer Korrektur bleibt der LCD bearbeitbar; erst ein erneuter expliziter Abschluss kann eine neue LCV erzeugen.
