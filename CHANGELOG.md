# CHANGELOG

## Unreleased

- Passive Flächen der Einstellungsübersicht und ihrer Detailseiten setzen beim
  Seitenwechsel wieder zuverlässig den Pfeilcursor, auch wenn der Mauszeiger
  stationär bleibt. Interaktive Karten und Buttons behalten ihren Handcursor.

- Ausgewählte interaktive Karten behalten ihren blauen Auswahlzustand und
  zeigen den Tastaturfokus zugleich mit dem zentralen teal Fokusrahmen.
  Hover, gedrückter und deaktivierter Zustand verdecken den Fokus nicht
  dauerhaft; Bedienlogik, Accessibility, Layout und Daten bleiben unverändert.

- Im Dashboard öffnet der große, per Maus, Enter und Leertaste bedienbare
  Hauptbereich eines passenden Kindes jetzt dessen Schülerprofil über die
  stabile `student_id`. Der getrennte Button `Beobachten` behält unverändert
  Fach- und Stundenkontext; beide Aktionen besitzen eindeutige Accessible
  Names und lösen einander nicht aus.

- Der Info-Button der Dashboard-Übersicht `Dokumentation im Überblick` öffnet
  nun per Maus, Enter und Leertaste eine sichtbare, schließbare und
  fokussierte Dokumentationshilfe. Sie erklärt den tatsächlichen aktuellen
  Zuordnungskontext und den nicht auf ein Schuljahr begrenzten Belegumfang,
  bleibt auch in kleinen Fenstern erreichbar und nimmt ausdrücklich keine
  Leistungs-, Entwicklungs-, Stärken-, Schwächen- oder Zielerreichungsdeutung
  vor.

- Beim Bearbeiten bestehender Beobachtungen bleiben nicht mehr registrierte
  oder leere gespeicherte Kontextwerte sichtbar neutral gekennzeichnet und
  werden ohne bewusste Neuauswahl unverändert gespeichert. Neue Beobachtungen
  bieten weiterhin nur die aktuell registrierten Kontexte an.

- LEG-Bereiche lassen sich wieder zuverlässig auf- und zuklappen, weil der
  vorhandene zentrale Disclosure-Feedback-Helper im Workspace sicher verfügbar
  ist. Tastatursteuerung, Accessibility, Inhalte und Persistenz bleiben
  unverändert.

- Die Oberfläche des Schuljahreswechsels führt jetzt in zwei klar getrennten
  Schritten durch Zuordnungsprüfung und verbindliche Aktivierung. Sie startet
  ruhig bei den ungelösten Fällen, zeigt fünf kompakte Kennzahlen, blendet
  weitere Filter und Sammelaktionen erst bei Bedarf ein und hält die
  vollständige Kindliste über `Alle Kinder` erreichbar. Der Abschluss besitzt
  eine eigene scrollbare Zusammenfassung; kleine Fenster ordnen Liste und
  externen Detailbereich untereinander an. Die rein technische Kursstufe wird
  nicht mehr als eigene Tabellenspalte wiederholt; Auswahlfelder entsprechen
  der appweiten Feldlogik und öffnen ihre vorhandenen Optionen ausreichend
  breit und hoch. Kursentscheidungen zeigen kompakte Kursnamen; nach einer
  individuellen Wahl bleibt der konkrete Zielkurs statt einer technischen
  Sammelbezeichnung sichtbar, ohne in der Optionsliste doppelt aufzutauchen.
  Beim ungelösten Kurs-3-Fall bleibt für den aktuellen Kurs ausschließlich die
  eindeutige Option `Verbleibt in <Kurs>` sichtbar.
  Die Sammelauswahl steht als kompakter, mittiger Block in der Karte. Auch die
  Zielstammgruppe zeigt den aktuellen Wert nur einmal und listet ausschließlich
  andere Gruppennamen ohne technische Präfixe. Der Zielstatus nennt für jede
  tatsächliche Stufenbewegung die konkrete Richtung, beispielsweise `1 → 3`
  oder `3 → 2`. `Ausgeschieden` und `Ungelöst` stehen getrennt vom als
  `Zielkurs` bezeichneten Kursauswahlfeld als sekundäre Aktionen bereit. Das
  missverständliche Suchkürzel entfällt,
  solange keine echte Textsuche Bestandteil des Dialogs ist. Plan-, Backup-,
  Step-up-,
  Maintenance-, Ausführungs- und Datenlogik bleiben unverändert.

- Der Schuljahreswechsel-Dialog blockiert ab Start der Aktivierung jetzt alle
  Qt-Schließpfade einschließlich nativer Fenstersteuerung, `reject()`,
  `done()`, Escape und Shell-Schließen. Nach sicherem Fehler oder Erfolg wird
  Schließen wieder freigegeben; `RECOVERY_REQUIRED` bleibt fail-closed.

- Die Schuljahreswechsel-Vorschau öffnet auf macOS ohne verschachtelten
  `QDialog.exec()`-Eventloop und wird nach jedem Schließen kontrolliert
  freigegeben. Individuelle Entscheidungen verwenden stabile, tastatur- und
  screenreaderzugängliche Auswahlfelder außerhalb der Accessibility-exponierten
  Tabelle; der Plan bleibt flüchtig und die Datenbank bis zur bewussten
  Aktivierung unverändert.
- Berichtswerkstatt und LEG-Workspace heben jetzt genau den aktiven lokalen
  Bereich beziehungsweise die aktive Phase mit der zentralen hellblauen
  Auswahlflaeche, kraeftiger Typografie, Rahmen und Auswahlmarker hervor.
  Inaktive Eintraege bleiben neutral; die LEG-Hinweise `Inhalt vorhanden` und
  `Noch leer`, Bericht-/LEG-Status, Tastatursteuerung, Fokus, Reduced Motion,
  Navigation, Drafts, Revisionen und Persistenz bleiben getrennt und
  unveraendert.
- Der synthetische Final-V3-Standardbestand führt `2025/26` jetzt geschlossen
  mit unveränderten historischen Assignments und genau ein `current`-Schuljahr
  `2026/27` mit vollständigen, eindeutigen `enrolled`-Assignments. Historische
  Beobachtungs-, Bestätigungs-, Berichts- und LEG-Referenzdaten bleiben
  unverändert; Transitiontests verwenden eine ausdrückliche
  2025/26-Pre-Transition-Fixture statt des Wandkalenders.
- SJ-3C.6 ergänzt die finale UI-Schutzstufe mit vollständiger Zusammenfassung,
  bewusster Prüfbestätigung, erneutem App-Passwort und zielbenannter
  Aktivierungsaktion. Ein Desktop-Worker verdrahtet den bestehenden Step-up-,
  Maintenance-, Backup- und Transition-Workflow, verhindert Doppelstarts und
  sperrt Dialog sowie App-Schließen während des kritischen Laufs. Erfolg lädt
  die App-Daten neu; Passwort-, Backup-, Frische-, Rollback- und
  `RECOVERY_REQUIRED`-Fehler bleiben ohne IDs, Hashes, Pfade oder Exceptions.
  Touch ID, Mehrkindwechsel, Build und Release bleiben ausgeschlossen.
- SJ-3C.5 ergänzt vor jedem Schuljahreswechsel eine verpflichtende Qt-freie
  Passwort-Step-up-Grenze. Erst ein vollständig gelöster Plan wird mit der
  vorhandenen `SecurityApplicationService.authenticate_password`-Prüfung
  authentifiziert; deren bestehende generische Status- und
  Drosselungssemantik bleibt unverändert. Ein Erfolg erzeugt ausschließlich
  im Prozess eine höchstens zwei Minuten gültige, an Planhash und Zweck
  `SCHOOL_YEAR_TRANSITION` gebundene Einmal-Autorisierung. Der Executor
  verbraucht sie vor `MAINTENANCE_PENDING`; Fehler, Ablauf, Abbruch und jeder
  Verbrauchsversuch verwerfen sie. Passwort- oder Credentialdaten gelangen
  weder in Autorisierung, Plan, Backupnachweis, Transitionbeleg noch Ergebnis.
  UI-/Shell-Ausführung, Bestätigungsaktion, Touch ID, Build und Release bleiben
  ausgeschlossen.
- SJ-3C.4 bindet die atomare Schuljahreswechsel-Ausführung verpflichtend an
  ein vollständig verifiziertes `.jkmbackup` des gedrainten Ausgangsstands.
  Der Qt-freie Service aktiviert ausschließlich eine passende
  `SCHOOL_YEAR_TRANSITION`-Capability aus `MAINTENANCE_PENDING`, erstellt und
  verifiziert das Backup unter `MAINTENANCE_ACTIVE`, bindet sichere Backup-ID,
  echten Archiv-Hash, Quellenhash, Final-V3-Schemafingerprint und
  Verifikationszeitpunkt und prüft Quellen sowie Plan danach erneut. Erst dann
  beginnt die atomare Transition; der Beleg speichert den echten Backup-Hash.
  Der Quellenhash wird aus der isoliert verifizierten Backup-Datenbank selbst
  berechnet; eine offene Observation-Recovery blockiert den Lauf, statt vor
  dem Pflichtbackup noch Datei- oder Datenbankwrites nachzuholen.
  Sichere Abbrüche rollen vollständig zurück und geben das Gate nach `NORMAL`
  frei; ein uneindeutiger Zustand bleibt fail-closed in `RECOVERY_REQUIRED`.
  Null-Sentinel, UI-/Shell-Ausführung, Build und Release sind nicht Bestandteil
  dieses Pakets; SJ-3C.5 ergänzt anschließend die Passwort-Step-up-Grenze.
- SJ-3C.3 ergänzt ein zentrales Qt-freies In-Process-Maintenance-Gate mit
  `NORMAL`, `MAINTENANCE_PENDING`, `MAINTENANCE_ACTIVE` und
  `RECOVERY_REQUIRED`. Ab `PENDING` werden neue fachliche Writer an der
  gemeinsamen produktiven Connection-Grenze blockiert; bereits zugelassene
  reentrante Datei-/Datenbankaggregate dürfen kontrolliert abschließen und
  `ACTIVE` wird erst nach vollständigem Drain erreichbar. Schüler- und
  Assignmentwrites, Gruppen/Kurse/Kursgruppen, Beobachtungen samt Anhängen,
  Bestätigungen, Dokumente, Berichts- und LEG-Drafts/Abschlüsse/PDFs,
  Stundenplan sowie fachliche Dokumentationseinstellungen sind geschützt.
  In diesem Zwischenstand verlangte der isolierte Transition-Service zusätzlich
  die ACTIVE Owner-Capability für den Zweck `SCHOOL_YEAR_TRANSITION`, während
  Backup/Restore noch unverdrahtet blieben. SJ-3C.4 ergänzt darauf aufbauend
  die Backupbindung und kontrollierte Gatefreigabe; SJ-3C.5 ergänzt danach die
  technische Step-up-Authentifizierung. UI, Ausführungsbutton und produktiver
  Shell-Aufruf wurden nicht ergänzt.
- SJ-3C.2 ergänzt die isolierte Qt-freie atomare Ausführungsgrenze für einen
  vollständig gelösten Schuljahreswechselplan auf ausschließlich temporären
  synthetischen Final-V3-Datenbanken. Plan und technische Quellen werden
  kanonisch per SHA-256 gebunden und vor jedem Write innerhalb genau einer
  `BEGIN IMMEDIATE`-Transaktion erneut geprüft. Ausgangsjahr, neues
  current-Zieljahr, genau ein `enrolled`- oder `exited`-Assignment je Kind und
  der unveränderliche technische Transitionbeleg werden gemeinsam committed;
  Counts, Constraints, `integrity_check` und `foreign_key_check` laufen vor
  Commit. Identischer Token und Plan liefern idempotent den vorhandenen Beleg,
  abweichende Retries sowie Fehler an jedem Schreibschritt werden ohne
  Teilumstellung abgelehnt beziehungsweise vollständig zurückgerollt.
  Historische Assignments und Fachrecords bleiben unverändert. Anzeigenamen
  gelangen weder in Plan-Hash noch Beleg. Dieser historische Zwischenstand
  besaß bewusst keine UI-, Backup-, Authentifizierungs- oder Maintenance-
  Integration und nutzte einen reservierten Null-Sentinel; SJ-3C.4 ersetzt
  diesen Sentinel im ausführbaren Pfad durch den echten Backup-Hash.
- Unter `Einstellungen → Schuljahre` ist jetzt der minimale Preview-only-
  Einstieg für den Schuljahreswechsel verfügbar. Die Unterseite zeigt das
  aktuelle Schuljahr und nimmt Bezeichnung, Beginn und Ende des neuen
  Schuljahres zugänglich per Tastatur und mit Accessible Names entgegen. Der
  vorhandene Read-Service validiert die Angaben und erzeugt Preview,
  Kurs-/Gruppenoptionen und den flüchtigen Plan aus demselben
  `query_only`-Snapshot; anschließend öffnet sich der bestehende
  Vorschau-/Bearbeitungsdialog. Ungültige Jahresdaten erscheinen neutral.
  Schließen verwirft alles. Es gibt weiterhin keine Ausführung, kein Backup,
  keine Passwortabfrage, kein Maintenance-Gate, keinen Write und keinen
  Transition-Beleg.
- Der bestätigte Restore-Handoff beendet die alte PySide-App jetzt über einen
  idempotenten, dialogfreien Shutdown statt über eine einzelne
  `QApplication.quit()`-Anforderung. Nach der ausdrücklichen
  Restore-Bestätigung werden noch offene Workspace-Eventloops kontrolliert
  beendet, alle Top-Level-Fenster verborgen, der normale Shell-`closeEvent`
  ausgeführt und erst danach der App-Eventloop verlassen. Dadurch hält weder
  eine versteckte Berichtswerkstatt noch ein nachgelagerter UI-Refresh den
  Parent-Lebensdauerkanal offen; der Restore-Worker kann ohne manuelles
  Fensterschließen fortfahren. Der Worker bestätigt `worker_started` und
  wartet nun außerdem vor Observation-Writer-Lock, Recovery, Preflight oder
  Live-Zugriff auf das vollständige Ende des alten Prozesses. Backupformat,
  Restore-Inhalte, Final-V3-Datenmodell, SQLite-/SQLCipher-, Security-,
  Keychain- und Support-Reset-Verträge bleiben unverändert.
- Bewusst ausgewählte Beobachtungsbelege werden in Berichtsvorschau und
  Entwurfs-PDF jetzt aus derselben vollständigen ViewModel-Projektion
  übernommen. Der PDF-Pfad verwirft keine gespeicherte Auswahl mehr wegen
  eines abweichenden zusätzlichen Zeitraumfilters; fachübergreifende Belege
  erscheinen genau einmal, die sichtbare Reihenfolge bleibt stabil und lange
  Notizen werden vollständig ausgegeben. Nicht ausgewählte Belege bleiben
  ausgeschlossen; nicht mehr auflösbare gespeicherte Bezüge
  werden kontrolliert und ohne sichtbare technische ID benannt. Historische
  Revisionen bleiben ausschließlich snapshotbasiert und deduplizieren
  fachübergreifend eingefrorene Belege ohne Änderung von Datenmodell,
  Snapshotformat oder allgemeiner PDF-Gestaltung.
- Der Entwurfs-PDF-Export aus der Berichtswerkstatt verwendet den geöffneten
  Arbeitsdialog jetzt als Owner für Dateiauswahl und Fehlermeldung und
  vermeidet den nativen verschachtelten macOS-Sheet-Eventloop. Erfolg, Abbruch
  und Exportfehler beenden dadurch nicht mehr den modalen Werkstatt-Lifecycle;
  ungespeicherte Gesamt- und Fachtexte, Belegauswahl, Dirty-State, aktiver
  Arbeitsbereich und Scrollposition bleiben erhalten. Der Export speichert
  keinen Draft, erzeugt keine Revision und verändert weder PDF-Inhalt noch
  Berichtsdatenmodell oder Snapshotformat.
- Berichtrevisionen bleiben nach dem Öffnen aus Schülerprofil oder
  Berichtswerkstatt stabil in ihrer schreibgeschützten historischen Ansicht.
  Der Revisionsdialog wird ohne verschachtelten modalen Eventloop über seine
  stabile Revisions-ID gehalten; allgemeine Profil- oder Berichtrefreshs
  ersetzen ihn nicht. Entwurf, Snapshot, Persistenz und PDF-Inhalt bleiben
  unverändert.
- Der normale App-Schluss entfernt jetzt alle sichtbaren Produktfenster und
  beendet den Hauptprozess kontrolliert. Eine nicht eingebettete
  `Alle Schüler`-Hinweisfläche war fälschlich ein eigenständiges
  Qt-Top-Level-Fenster und hielt dadurch `lastWindowClosed` sowie den
  Restore-Worker-Handoff offen. Die ungenutzte Hinweisfläche wurde entfernt;
  weitere dauerhaft vorgehaltene, nicht sichtbare Profil-Hilfswidgets besitzen
  nun den Schülerprofil- beziehungsweise Berichtsbereich als expliziten
  Qt-Owner; ausgetauschte Profil- und Berichtsvorschau-Karten werden
  kontrolliert per `deleteLater()` zerstört, ohne als Hilfsfenster zu
  verbleiben. Fachlogik, Datenmodell, Restore-Reihenfolge und
  Neustartprotokoll bleiben unverändert.
- SJ-3A ergänzt die rein lesende, Qt-freie Vorschau für einen
  Schuljahreswechsel. Ein connection-gebundener `query_only`-Snapshot liest
  alle V3-Kinder, ihre Assignmentkandidaten am Ende des eindeutigen
  current-Schuljahres sowie vorhandene Schuljahre, Gruppen und Kurse.
  Fortschreibung erfolgt ausschließlich über `courses.year_level`: 1→2 und
  2→3 werden nur bei genau einem aktiven Zielkurs vorgeschlagen, Stufe 3
  bleibt ungelöst, eine gültige aktive Stammgruppe unverändert. Archivierte,
  ausgeschiedene, fehlende, mehrdeutige oder ungültig zugeordnete Kinder
  bleiben vollständig sichtbar und blockierend. Zieljahresüberlappung und
  -lücke blockieren die Gesamtprojektion. SJ-3A selbst enthält keine UI,
  Datenbankwrites, Planpersistenz, Aktivierung, Authentifizierung, Backup-
  oder Mehrkindwechselfunktion.
- SJ-3B.1 zeigt die vorhandene Schuljahreswechsel-Preview in einem isolierten
  rein lesenden PySide-Dialog. Kopf, Zähler, Zielstatus, Warnungen und jedes
  Preview-Item werden ohne Neuberechnung oder Sortierung dargestellt.
  `Ungelöst` bleibt als Text sichtbar; Tabelle, Zellen, Status und Schließen
  besitzen zugängliche Namen beziehungsweise Beschreibungen. Der Dialog
  besitzt keine Kurs-/Stammgruppenwahl, Checkbox, Repository-, Write-,
  Backup-, Authentifizierungs- oder Ausführungsaktion. Settings-/Shell-
  Integration und der editierbare flüchtige Plan bleiben SJ-3B.2.
- SJ-3B.2a ergänzt `SchoolYearTransitionPreviewItem` um den ausschließlich aus
  V3-Schülerstammdaten aufgelösten Anzeigenamen bei stabiler `student_id`.
  Fehlende referenzierte Stammdaten bleiben als `Name nicht verfügbar` und
  Blocker sichtbar. Ein neues unveränderliches Application-Planmodell bildet
  Vorschlag übernehmen, anderen aktiven Kurs, Kurs 3 wiederholen,
  ausgeschieden, ungelöst sowie unveränderte oder andere aktive Stammgruppe
  rein flüchtig ab. Ursprüngliche Issues bleiben erhalten; deterministische
  Validierung und Zähler führen weder Qt-, Repository-, SQLite-, Backup-,
  Authentifizierungs-, Persistenz- noch Ausführungslogik aus.
- SJ-3B.2b stellt den flüchtigen Schuljahreswechsel-Plan im vorhandenen
  Vorschau-Dialog individuell je Kind dar. Sichtbar sind Schülername,
  bisherige Stammgruppe, Kurs und Kursstufe sowie Zielstatus, Zielgruppe,
  Zielkurs und textliche Warnungen oder Blocker. Vorschlag, anderer aktiver
  Kurs, Kurs-3-Wiederholung, unveränderte oder andere aktive Stammgruppe,
  Austritt und bewusst ungelöst werden ausschließlich über die vorhandenen
  Planmethoden als neue unveränderliche Instanz übernommen; Planstatus und
  Zähler aktualisieren sich danach. Das Öffnen eines Auswahlfelds entscheidet
  nichts. Global bleibt nur Schließen; es gibt keine Mehrfachauswahl,
  Sammelaktion, Datenbankwrites, Repositoryaufrufe, Shell-/Settings-
  Integration, Ausführung, Backup oder Authentifizierung.
- SJ-3B.3 ergänzt den bestehenden Dialog um kombinierbare Filter für ungelöste
  Kinder sowie bisherigen und geplanten Kurs beziehungsweise bisherige und
  geplante Stammgruppe. Sichtbare Zeilen können einzeln oder vollständig
  ausgewählt werden; ein Filterwechsel entscheidet und selektiert nichts.
  Verdeckte ausgewählte Kinder bleiben erkennbar ausgewählt, werden aber von
  einer Sammeländerung im aktuellen Filter nicht unbeabsichtigt erfasst.
  Zielkurs, Zielstammgruppe, ausgeschieden und bewusst ungelöst werden für die
  ausgewählten sichtbaren Kinder ausschließlich über einen neuen flüchtigen
  Plan übernommen. Mehrkindänderungen verlangen eine Bestätigung, Kursstufe 3
  bleibt bis zur bewussten Kurs-3-Auswahl ungelöst und ausgeschieden entfernt
  Kurs und Stammgruppe. Zähler, textlicher Gesamtstatus und sichtbarer
  Auswahlstand aktualisieren sich unmittelbar. Es gibt weiterhin keine
  Datenbankwrites, Repositoryaufrufe, Shell-/Settings-Integration,
  Ausführung, Backup oder Authentifizierung.
- Die normale Runtime lässt ausschließlich ein vollständig verifiziertes
  Final-V3 als `V3_SCHEMA_READY` zu. Unbekannte, beschädigte oder unsichere
  Schemata, WAL-/SHM-Sidecars, offene Restorezustände und fehlende
  Datenbanken außerhalb eines autorisierten First Runs bleiben fail-closed.
  Nach erfolgreichem Gate öffnet die Composition Root die vorhandene
  Datenbank ohne Create-Fallback; ein Verschwinden zwischen Gate und
  Shell-Konstruktion erzeugt keinen Ersatzbestand. Ein autorisierter First Run
  erzeugt nur das Final-V3-Schema und kein Schuljahr. Fehlt ein eindeutiges
  `current`-Schuljahr, startet die Runtime technisch und sperrt die
  schülerbezogenen Bereiche fachlich. Der isolierte Packaged Smoke behandelt
  diesen leeren Zustand kontrolliert. Restorediagnosen benennen das geprüfte
  Final-V3 korrekt. Es wurden keine Migration, echten Daten,
  Schuljahreswechsel- oder Mehrkindwechselfunktionen ergänzt. Die manuelle
  macOS-Abnahme bleibt offen. 400 fokussierte
  Startup-/Security-/Restore-/Runtime-/Shell-Tests und 48 Subtests sowie die
  vollständige Gesamtsuite mit 1811 Tests und 71 Subtests bestanden; ein
  umgebungsgebundener Test blieb übersprungen. Ein einmaliger unveränderter
  Security-Parallelitätstest mit SQLite-Lock bestand isoliert und im
  abschließenden vollständigen Wiederholungslauf.
- SJ-2F stellt sämtliche produktiven Schüler-, Kurs- und
  Stammgruppen-Schreibpfade auf Final-V3 um. Schüleranlage persistiert
  V3-Stammdaten und initiales `enrolled`-Assignment in einer Transaktion;
  Stammdatenbearbeitung, datierter Einzelwechsel, Austritt und Archivierung
  verwenden getrennte Lifecycles. Austritt archiviert nicht, Archivierung
  ändert kein Assignment und wird bei aktueller Einschreibung blockiert. Die
  generischen V2-Schülercommands, produktiven Writes auf
  `students.group_id/course_id` und die testlokale
  Legacy-Membershipfixture sind entfernt. Kurse verlangen eine bewusst
  gewählte `year_level` 1, 2 oder 3; Kurs- und
  Stammgruppendeaktivierung wird bei aktuellen oder zukünftigen
  `enrolled`-Assignments ohne Membershipmutation blockiert. Der normale
  synthetische Entwicklungs-/Testdatenpfad erzeugt deterministisch eine
  frische Final-V3-Datenbank mit current-Schuljahr `2025/26`, Kursstufen,
  V3-Schülern und vollständigen Assignments; es wurden weder echte Daten
  migriert noch vorhandene lokale Datenbanken überschrieben. Nach drei
  begrenzten Fixzyklen bestanden 82 fokussierte
  Final-V3-Schema-/Assignment-/MasterData-/Produktwriter-Tests sowie die
  vollständige Gesamtsuite mit 1808 Tests und 71 Subtests; ein bestehender
  umgebungsgebundener Test blieb übersprungen. `compileall`, Importisolation,
  Writer-/Legacy-Suchgate und `git diff --check` waren grün. Die manuelle
  macOS-UI-Prüfung steht noch aus. Die Runtime bleibt
  `V3_SCHEMA_READY_BUT_RUNTIME_NOT_MIGRATED`; Schuljahreswechsel-Assistent und
  Mehrkindwechsel bleiben offen.
- SJ-2E stellt sämtliche produktiven Kurs- und Stammgruppen-Lesepfade auf die
  zentrale V3-Assignment-API um. Schülerlisten und -profil, Gruppen, Kurse,
  Kursverbünde, Dashboard, Beobachtungsbearbeitung, Berichtsvorbereitung und
  -finalisierung sowie LEG-Vorbereitung und -Abschluss verwenden explizite
  Snapshot- beziehungsweise Referenzdaten; `observations.date`, `period_end`
  und `conference_date` werden nicht durch heutige oder letzte bekannte
  Zuordnung ersetzt. `CurrentMembershipReadSnapshot` liefert zentrale Counts
  und blockierende Current-Year-/Mehrdeutigkeitsdiagnostik;
  `AssignmentReferenceRequest` unterstützt wiederholte Kinder an
  unterschiedlichen Stichtagen in einer Batchabfrage. Report- und
  LEG-Snapshot samt historischer Gruppe/Kurs entstehen jeweils innerhalb
  derselben Transaktion; bestehende Revisionen, Hashes und PDF-Artefakte
  bleiben unverändert. Produktive V2-Membershipreads und N+1-Auflösung sind
  entfernt. Ausschließlich bestehende synthetische V2-Writerregressionen
  verwenden einen ausdrücklich testlokalen Projektions-Double; alle neuen
  Daten- und Produktlesetests erzeugen temporäre Final-V3-Datenbanken. 163
  fokussierte SJ-2E-/betroffene Tests sowie die Gesamtsuite mit 1788 Tests und
  71 Subtests waren grün; ein vorhandener umgebungsgebundener Test blieb
  übersprungen. Compileall, Importisolation und `git diff --check` waren grün.
  Die normale Shell bleibt
  `V3_SCHEMA_READY_BUT_RUNTIME_NOT_MIGRATED`; Writerumstellung,
  Schuljahreswechsel-Assistent, Sammelwechsel, Build, Packaging und Release
  bleiben gesperrt.
- Zentrale Qt-freie V3-Assignment-API ergänzt: Connection-gebundene
  Schuljahres-, Assignment- und V3-Schüler-Repositories, konsistente
  Read-Snapshots, explizite Datums- und Schuljahresauflösung, set-basierte
  Batchabfragen für 1/10/100 Kinder, Gruppen-, Kurs- und Kursverbundfilter
  sowie neutrale Auflösungszustände ohne Systemdatums- oder
  Last-known-Fallback. Das V3-Schülermodell enthält keine Membershipfelder.
  Anlage mit initialer Einschreibung, Stammdatenänderung, Einzeleinschreibung,
  unterjähriger Einzelwechsel, Austritt und Archivierung besitzen getrennte
  atomare Lifecycles; Austritt archiviert nicht, Archivierung verändert kein
  Assignment. Produktive Leser, Runtime, Schuljahreswechsel-UI, Build und
  Release bleiben gesperrt.
- V3-only Architecture Cleanup technisch umgesetzt: Das vollständige finale
  Schema wird ohne Vorgängerschema direkt durch `FinalV3SchemaInitializer`
  erzeugt und mit `user_version = 3`, vollständigem Fingerprint
  `d75b803552ba961bff5578ec0853c1d0a2d035845db6a7b624b1528cf546e731`,
  Integritäts- und Fremdschlüsselprüfung verifiziert.
  `school_year_transitions.from_school_year_id` ist für echte Wechsel
  verpflichtend; Initialanlagen schreiben keinen Übergangsbeleg. Die
  V2→V3-Engine, Cutover-Evidence, Klassifizierung, Failpoints,
  V2-Startupzustände und V1/V2-Restoremigration sind entfernt. Compatibility,
  Backup und Restore akzeptieren ausschließlich Final-V3; Backupformat-v1
  bleibt als unabhängiger Containervertrag bestehen. Der neue temporäre
  Testdatenpfad erzeugt deterministisch Schuljahr 2025/26, Kursstufen 1–3,
  Gruppen, V3-Schüler, vollständige Assignments sowie synthetische
  Beobachtungs-, Bestätigungs-, Berichts- und LEG-Daten. Die normale Shell
  bleibt bis zur Leser-/Writerumstellung mit
  `V3_SCHEMA_READY_BUT_RUNTIME_NOT_MIGRATED` gesperrt.
- ADR-096 legt V3 als erstes und einziges Produktschema fest. Es existieren
  keine produktiven V2-Daten; bisherige V2-Bestände sind ausschließlich
  synthetische Entwicklungsdaten und werden nicht migriert. Die in den
  nachfolgenden historischen SJ-1-/SJ-2A-/SJ-2B-/SJ-2C-Einträgen beschriebenen
  V2-Cutover-, Bootstrap- und V2-Restore-Annahmen sind damit verworfen.
  School-Year-/Assignment-Datenhoheit und die Sicherheitsgrenzen für echte
  spätere Schuljahreswechsel bleiben bestehen. Dieser Governance-Schritt
  beschließt das Produktschema; technischer Cleanup, produktive Leserumstellung
  und Runtime-Freigabe sind noch nicht umgesetzt.
- SJ-2C als Qt-freie, read-only Datenbank-Startup- und
  Bootstrap-Routinggrenze ergänzt. Nach Restore und Authentifizierung, aber
  vor fachlicher Runtime-Vorbereitung, Shell, Adaptern, Schemainitialisierung
  und Default-Writern werden fehlende, exakte V2-, exakte V3-, unbekannte und
  Recoveryzustände getrennt klassifiziert. Exaktes V2 wird ohne Schreibzugriff
  in `V2_BOOTSTRAP_READY` geroutet; exaktes V3 wird erkannt, bleibt wegen der
  V2-gebundenen Runtimepfade aber gesperrt. Ein echter First Run behält die
  bestehende V2-Neuanlage, während installierte Initialdaten vor der Shell
  erneut klassifiziert werden. Die Neuanlage ist an
  `SecurityStartState.FIRST_RUN` gebunden; eine fehlende Datenbank in einer
  bestehenden Installation sowie vorhandene WAL-/SHM-Sidecars führen
  fail-closed zu `RECOVERY_REQUIRED`. `DATABASE_COMPATIBILITY_VERSION` bleibt `2`;
  es gibt keine automatische Migration, keine Änderung einer vorhandenen
  produktiven V2-Datenbank, keinen Bootstrap-Assistenten und keine
  V3-Fachaktivierung. 34 fokussierte SJ-2C-Tests sowie die Gesamtsuite mit
  1872 Tests und 71 Subtests waren grün; ein umgebungsgebundener read-only
  Build-303-Referenztest blieb erwartungsgemäß übersprungen. Unabhängiger
  Technical- und Governance-Review ergab keine verbleibenden Findings.
- SJ-2B als isoliertes V3-Zielschema und explizite V2→V3-Migrationsengine
  ergänzt. Das Ziel enthält `school_years`, datierte
  `student_school_year_assignments`, unveränderliche
  `school_year_transitions`, bestätigtes `courses.year_level` und
  V3-`students` ohne Legacy-Mitgliedschaftsspalten. Planformat v2 bindet den
  vollständigen kanonisch gehashten Quellzustand; unveränderliche
  `VerifiedBackupEvidence` ist verpflichtende Eingabe, die Engine erzeugt
  selbst kein Backup. Der exakte Zielfingerprint ist
  `640a10a76b292eca3a2ba47255711db87e27d4eaa1580fcc58086035cb8d6cd1`.
  Atomare Migration, vollständiger Pre-Commit-Rollback, committed
  Post-Commit-Recoveryzustände, Reopen-Verifikation und injizierte Failpoints
  wurden ausschließlich auf synthetischen temporären SQLite- und
  SQLCipher-Datenbanken geprüft. 120 fokussierte Tests, 237
  V2-Regressionsprüfungen mit 8 Subtests und die Gesamtsuite mit 1838 Tests
  und 71 Subtests waren grün; ein umgebungsgebundener read-only
  Build-303-Referenztest blieb erwartungsgemäß übersprungen. Normaler Startup,
  aktive
  Kompatibilitätsversion und Runtime bleiben V2; es gibt keinen Bootstrap,
  keine UI, keine automatische oder reale Migration und keine
  Produktaktivierung.
- SJ-2A als reine, SQLite- und Qt-freie Core-Domain ergänzt:
  `SchoolYear`, inklusive `StudentMembershipAssignment`,
  vollständige V2-Schülerklassifikation mit getrennten Warncodes,
  read-only Initialisierungsvorschau, bestätigte Kursstufen,
  Quell-/Ziel-Schemainformationen und kanonischer
  `SchoolYearInitializationPlan`. Die Planserialisierung verwendet UTF-8,
  Unicode NFC, sortierte JSON-Schlüssel, explizit stabile Arrayreihenfolgen
  und ISO-Daten; `plan_sha256` hasht exakt diesen Payload. Es entstanden keine
  Tabelle, Migration, Schema-, Startup-, UI- oder V2-Produktpfadänderung.
- SJ-1-Governance- und Architekturvertrag für den Schuljahreswechsel
  dokumentiert. ADR-095 legt `school_years` und datierte
  `student_school_year_assignments` als einzige zukünftige Sources of Truth,
  stabile `courses.year_level`, unterjährige Intervalle, Schuljahreswechsel,
  separaten Kurs-/Stammgruppen-Sammelwechsel, Austritt ohne Archivierung,
  fachliche Historienzeitpunkte, unveränderliche Bericht-/LEG-Revisionen,
  Maintenance, Backup, Passwort-Step-up, Idempotenz, Rollback und den
  erwarteten V2→V3-Cutover fest. Die zuständigen Registries enthalten
  Datenmodell-, Lifecycle-, Ownership-, UI- und Accessibility-Verträge.
  Bestehende Pilotwerte für `2025/26` bleiben ausschließlich
  bestätigungspflichtige Vorbelegung. Keine Code-, Schema-, Migrations-, Test-,
  Build-, Packaging- oder Releaseänderung. Die letzte bekannte
  Legacy-Governance-Lücke ist geschlossen: Jeder V2-`StudentRecord` wird genau
  einmal klassifiziert; aktive eindeutige Fälle erhalten volle
  Initialintervalle, archivierte eindeutige Fälle ein historisches
  `enrolled`-Intervall bis zum Vortag des lokal normalisierten
  `archived_at`-Datums. Archivierung wird nicht als Austritt gedeutet;
  zeitlich unklare, ungültige und widersprüchliche Fälle blockieren. Erkannte
  V2-Bestände bleiben bis zum kontrollierten Initialisierungs-/Migrationsmodus
  von regulärer V3-Fachnutzung getrennt.
- Phase 2 der Berichte-Übersicht lokal implementiert: deterministische
  RPD-Projektion, ein Ereignis je Beobachtung beziehungsweise abgeschlossenem
  Bericht-/LEG-Aggregat, aktueller sicherer Bestätigungsstand, Zielumfang 15,
  inklusive Zeitraumfilterung und getrennte hashverifizierte Bericht-/LEG-
  Batchreads. Die UI zeigt absolute Fachsegmente ohne Nenner oder Restspur,
  kleine fachbezogene Orientierungssymbole und die vollständige chronologische
  Timeline horizontal mit verbundener Meilensteinachse, kompakten runden
  Ereignismarkern, 2/4/5-Viewport, Scrollbar, Steuerbuttons,
  Tastaturbedienung und stabiler ID-Navigation. Die großen voneinander
  getrennten Timeline-Inhaltskarten wurden zugunsten der ruhigeren
  Paket-1-Formsprache wieder entfernt. Die früheren neutralen
  Platzhalterkarten `Stärken` und `Im Blick behalten` entfallen im
  Berichtsbereich vollständig. Keine neue Tabelle, Migration, Schreiblogik
  oder Persistenz. Reale macOS-Trackpad- und VoiceOver-Abnahme, Build,
  Packaging, Push, Tag und Release bleiben offen beziehungsweise wurden nicht
  ausgeführt.
- Den vor der technischen Umsetzung beschlossenen Phase-2-Architektur- und
  UX-Stand der Berichte-Übersicht in die bestehenden Governance-Sources-
  of-Truth integriert und an den finalen Belegworkflow angeglichen. ADR-094
  hält die rein lesende RPD-, Ereignis-, Aggregat-, Deduplizierungs-,
  Bestätigungs- und getrennte Bericht-/LEG-Architektur fest; Technical Naming
  Registry, Data Registry, Data Lifecycle, View Ownership, UI-Mapping und
  Design-System enthalten ihre jeweils zuständigen Verträge. Eine Beobachtung,
  ein Berichtaggregat und ein LEG-Aggregat erzeugen jeweils höchstens eine
  Timeline-Karte; Kompetenzzuordnungen erzeugen keine eigenen Timeline-Karten.
  LEG verwendet `conference_date`, technische Revisionen bleiben in ihren
  Revisionshistorien. Der Berichtsbereich bleibt eine neutrale Belegübersicht
  und keine Entwicklungsanalyse.
  Paket 1 und Paket 1.1 bleiben als implementierter, nicht
  Phase-2-konformer Stand getrennt dokumentiert. Der Architektur-/UX-Vertrag
  und der Product-Decision-Freeze bleiben Herkunfts- und Abnahmenachweise,
  aber keine konkurrierende Governance-Quelle. Dieser getrennte
  Governance-Basisstand enthielt noch keine Code-, Datenmodell-, Migrations-,
  Test-, Build-, Packaging- oder Releaseänderung.
- Paket 1.1 der Berichte-Übersicht visuell verdichtet: höchstens vier Fächer vor bewusster
  Erweiterung, platzbegrenzte Meilensteine aus vorhandenen Bericht-/LEG- und
  Bestätigungsereignissen, eindeutige LEG-Aktionen sowie Entfernung der
  redundanten unteren Arbeitsraumkarten. Die Fachkacheln zeigen vorhandene
  neutrale Dokumentations- und Beobachtungszahlen mit denselben Kreisdiagrammen
  wie das Schülerprofil und ohne Qualitätsbadge; die
  Meilensteine verwenden Monatskürzel, eine verbindende Linie und
  typspezifische Icons. Kompetenzbestätigung bleibt ausdrücklich von einem
  nicht vorhandenen Kompetenzabschluss getrennt.
- Jeder neue Berichtsentwurf verlangt nun unabhängig von bereits vorhandenen
  Entwürfen eine bewusste, nicht persistente Zeitraumwahl, bevor sich der
  bestehende Berichtarbeitsraum öffnet.
- Berichte-Übersicht im Schülerprofil für Paket 1 vorbereitet: getrennte
  Bericht-/LEG-Statuskarten, eindeutiger RPD-Zeitraum, sichere Mehrfachauswahl,
  gemeinsame read-only Historienanzeige, konkrete nächste Schritte und
  Fachsprunganker zum einzigen bestehenden Berichtarbeitsraum.
- Zeitleiste, Stärken- und Beobachtungsschwerpunktflächen bleiben neutrale
  Leerzustände; keine neue Persistenz, Kompetenzlogik, automatische
  Entwurfswahl oder Schuljahressemantik ergänzt.
- Wiederaufnehmbare lokale Pilot-Releaseautomation mit kanonischer nicht
  geheimer Konfiguration, detached Clean-Build, manifestgebundenen Assets,
  getrennten Paketgates, GitHub-Draft-/Rückdownloadprüfung, signierter
  Pilot-Appcast-Publikation, öffentlicher Endverifikation, Dry-run und
  Stable-Schutz ergänzt.
- Build 303 als unveränderliche veröffentlichte read-only Referenz für Tag,
  Pre-Release, Assetmetadaten und Pilot-Appcast dokumentiert; historische
  Vorbereitungsnachweise bleiben als damaliger Stand gekennzeichnet.
- Aktive Kursverbünde samt Stammgruppen- und Kurszuordnungen sind Teil des
  transaktionskonsistenten Schüler-/Dashboard-Projektionssnapshots; die
  Dashboard-Auflösung liest nach dem Batch keine zweite Verbindung und ihr
  Querybudget bleibt unabhängig von der Kursverbundanzahl konstant.
- Schülerliste und Dashboard-Heatmap lesen ihre kanonische
  Dokumentationsprojektion transaktionskonsistent gebündelt; Abfragen je
  Schüler oder Beobachtung sowie Schemainitialisierung in reinen
  Read-Konstruktoren entfallen, ohne Datenmodell-, Index- oder Statusänderung.
- Neue Beobachtungs-IDs werden im selben serialisierten SQLite-Schreibvorgang
  aus einem schmalen ID-Read vergeben; der vollständige Beobachtungsbestand
  samt Kompetenzbewertungen wird dafür nicht mehr hydriert.
- Bericht- und LEG-Entwürfe bei vorhandenem Arbeitsstand bewusst auswählen
  lassen: vorhandenen Entwurf öffnen, neuen eigenständigen Entwurf beginnen
  oder ohne Datenänderung abbrechen. Ältere Entwürfe bleiben erreichbar.
- Bestätigungsfrische auf eine monotone append-only Ereignisreihenfolge
  umgestellt; historische Observation-/Confirmation-Gleichstände bleiben
  sichtbar unklar, bis bewusst erneut bestätigt wird.
- Speichern von Beobachtung und Anhängen als idempotenten, crash-fortsetzbaren
  Unit-of-Work mit kontrolliertem Dateistaging, No-Clobber-Publikation und
  gemeinsamer SQLite-Transaktion vorbereitet.
- Datenbank-Kompatibilitätsversion 2 mit transaktionaler V1-Migration und
  Restore-Staging-Kompatibilität eingeführt; keine allgemeine Indexbereinigung.
- Zentrales Motion-System um ruhige Button-, Dialog-, Sidebar-, Segment-,
  Bewertungs- und Speicherbestätigungs-Mikrointeraktionen erweitert; Bericht
  und LEG überblenden ausschließlich den neu aktiven lokalen Inhalt.
- Toast-Ein- und -Ausblendung auf 220 ms vereinheitlicht, interaktive Karten
  auf 100 ms Hover-Reaktion präzisiert und sämtliche neuen Übergänge an die
  bestehende Reduced-Motion-Policy gebunden.
- Tabellen, große Listen, Scrollen, Baumstrukturen, Dokument-/PDF-Vorschauen,
  komplette Shell-Fenster und Dashboard-Daueranimationen bleiben bewusst
  statisch.
- Alle produktinternen Bestätigungsdialoge mit Qt-Standardfragen verwenden
  explizite deutsche Aktionsverben sowie eine sichere Abbrechen-, Enter- und
  Escape-Belegung.
- Passwortanlage, Passwortbestätigung, Login und Passwortwechsel verwenden
  öffentliche sensitive Qt-Eingabehinweise und eindeutige Accessible Names;
  der native macOS-Passwortvorschlag bleibt bis zum echten Bundle-Test offen.
- Touch ID bleibt bei fehlendem Credential, Secret, eingerichteter Biometrie
  oder Verfügbarkeit auf unterstützten Macs mit verständlichem Grund sichtbar;
  Passwort-Fallback und explizite Credential-Anlage bleiben unverändert.
- Zentrale Version auf `0.3.0` / Build `303` angehoben. Der paketierte
  Restore-Neustart startet eine neue, unabhängige PyInstaller-Instanz mit
  gültigen Standardkanälen und erkennt einen vor dem Startup-Handshake
  beendeten Kindprozess samt Exitcode. Builds 300 bis 302 wurden nicht
  verteilt; für Build 303 existiert in diesem Stand noch kein Appcast- oder
  Releaseartefakt.
- Benutzerhandbuch, aktuelle ausschließlich synthetische Screenshots,
  Sicherheitsdokumentation und interne Releasebasis auf den produktiven
  Gate-Off-Pfad, Restore-Worker, Entwurfsauswahl und UX-Hardening ausgerichtet.
- Paketierten Restore-Worker erst nach authentisierter Lock-/Handoff-Uebernahme
  als gestartet behandeln; der Worker wartet bis zum vollstaendigen Ende der
  Haupt-App, waehrend fehlende oder sofort fehlschlagende Starts ohne
  Live-Datenmutation in der geoeffneten UI gemeldet werden.
- Stabilität des realen SQLite-Backup-Sperrtests verbessert: Der Test prüft
  weiter Retry, begrenztes Warten, `BackupBusyError` und Snapshot-Cleanup,
  koppelt sich aber nicht an eine nicht spezifizierte Callback-Anzahl der
  SQLite-C-API.
- Qt-Backup-/Restore-Worker erst nach bestätigtem nativem Thread-Ende zur
  Löschung vormerken, damit ausstehende Qt-Events keinen bereits zerstörten
  PySide-Threadwrapper erreichen.
- Manipulationsprüfung beim Streamen einer verwalteten Backup-Datei an den
  ersten tatsächlich gelesenen Chunk gebunden statt an ein zeitabhängiges
  Polling auf ein Stagingziel.
- Lokale Sicherheitslaufzeitdaten, Einstellungen und die Instanzsperre werden
  nicht mehr als unversionierte Repositoryänderungen angezeigt.

## Security Sprint 12 - Release-Hardening für internen 0.3.0-RC

### Changed

- Produkt- und Bundleversion auf `0.3.0` / Build `300` vereinheitlicht und im
  bestehenden Über-Dialog sichtbar gemacht.
- macOS-Build um exakt gepinnte PyNaCl-/libsodium- und
  sqlcipher3-/SQLCipher-Testlaufzeiten, explizite Hidden Imports und gebündelte
  Security-Lizenztexte ergänzt.
- Build- und Distributionsziele auf validierte Projekt-/Temporärwurzeln
  begrenzt; universelle Mach-O-Dateien vor Codesign auf arm64 reduziert.

### Added

- Doppelt markergebundenen internen Pakettest für Migration,
  Dokumentcontainer, verschlüsseltes Backup, Restore-Staging, Reopen,
  falschen Key, Manipulation, Gate-Off-Bestand und echte Crash-Recovery
  ergänzt.
- Separaten realen macOS-Keychain-Pakettest für DMK-Provisionierung,
  Prozess-/Bundle-Reopen, Passwortwechsel ohne Rotation, fehlenden/falschen
  Eintrag und Cleanup ergänzt.
- Vor-PyInstaller-Laufzeitaudit sowie statischen Bundle-, Architektur-,
  Lizenz-, Artefakt- und Entwicklerpfadscan ergänzt.
- DMG-Erzeugung gegen die asynchrone Finder-Mount-Sichtbarkeit gehärtet und
  den Qt-Responsivitätstest deterministisch an einen real verarbeiteten
  Hauptthread-Timer-Tick gebunden.

### Tests

- Finaler interner arm64-Build einschließlich Gate-Off, 23 Gate-On-Schritten,
  vier echten Crash-Recoveries, realem Keychain-Lifecycle, 141
  arm64-Mach-O-Prüfungen und DMG-Erzeugung grün.
- Gesamtsuite final mit 1.625 bestandenen und 20 bestehenden
  plattformgebundenen übersprungenen Tests grün; 576 Security-/Support-/
  Backup-/Restore-Fokustests sowie wiederholte Qt-Reihenfolgeläufe grün.
- `compileall`, `pip check`, Build-Syntax, Codesign-, Lizenz-, Secret-,
  Artefakt-, Entwicklerpfad- und Klartextprüfungen bestanden.

### Boundaries

- Normaler Gate-Off-Startup importiert keinen Integrationsorchestrator und
  bleibt beim bestehenden SQLite-, Dokument- und ZIP-v1-Pfad.
- SQLCipher Community 4.12.0 ist nur die explizite interne
  Sprint-11-Testengine; SQLCipher 4.17.0 bleibt Produktgate.
- Keine Produkt-/Pilotmigration, keine Recovery-UI, kein Stable-Appcast, keine
  Windows-Freigabe, keine Developer-ID-/Notarisierungsbehauptung und keine
  rechtliche Compliance-Aussage.

## Security Sprint 11 - kontrollierte Integration hinter inaktivem Gate

### Architecture

- Verbindliche Integrationsmatrix und den vollständigen Datenfluss von
  Gate-/Startupprüfung bis verifiziertem Restore-Staging dokumentiert.
- Markergebundenen temporären Test-Root, zentrale SQLCipher-Connection-Factory,
  `SecurityIntegrationSchemaV1`, atomare Dokumentpointer, HMAC-Journal,
  externen Replay-Anker und restartfähige Phasen als einzige Sprint-11-
  Integrationsgrenze festgelegt.
- Produkt-, Pilot-, RC-, UI-, ZIP-v1-, Packaging-, Build-, Appcast-, Release-,
  Identity-VFS-, Capability-, `ATTACH`- und `sqlcipher_export`-Pfade
  ausgeschlossen.

### Added

- Kleinsten vollständigen End-to-End-Pfad für markierte
  Klartext-Testinstallationen hinter `JKM_SECURITY_INTEGRATION_TEST=1`
  implementiert: Safety Copy, VFS-freier SQLCipher-Transfer, versioniertes
  Dokumentgenerationsschema, verifizierte Container, atomare Pointer,
  verschlüsseltes Backup, frischer Reopen und Restore-Staging.
- HMAC-authentisiertes Journal und getrennten pending/committed Replay-Anker
  mit explizit evidenzgebundener Übernahme eines verwaisten Migrations-Locks
  ergänzt; normale Starts übernehmen keinen Stale-Lock automatisch.
- Qt-freien Application Adapter für kontrolliertes Lesen, bewussten
  No-Clobber-Klartextexport, idempotentes Vorbereiten einer Ersatzgeneration,
  atomaren Generationswechsel und explizit aufgeschobenes Löschen ergänzt.
- Zentrale SQLite-/SQLCipher-Provider um schreibfreie Opens erweitert; der
  Security-Layer importiert keinen Datenbanktreiber direkt.

### Tests

- 24 Sprint-11-Fokus- und echte Crash-Subprozesstests grün; geprüft sind unter
  anderem Gate-Off bei vorhandenem Testbestand, Symlink-/Pfadgrenzen,
  Schlüssel- und Artefaktmanipulation, Klartext im Storage, Konkurrenz,
  Dokumentaustausch, Export, Backup/Restore sowie idempotente Recovery an
  jeder Orchestrator-Phasengrenze.
- 184 Sprint-8–10-Foundationtests sowie 536 relevante Produkt-, Startup-,
  Support-, Backup-, Restore- und Adaptertests mit 48 Subtests grün.
- Gesamtsuite: 1619 bestanden, 20 bestehende plattformgebundene Tests
  übersprungen, 67 Subtests bestanden; `compileall`, `pip check` und
  `git diff --check` bestanden.

### Boundaries

- Ohne Gate bleibt der Produktpfad unverändert und importiert den
  Sprint-11-Orchestrator nicht. Keine UI, Produktmigration, Pilot-/RC-
  Aktivierung, Klartextlöschung, physisches GC, Packaging, Build oder Release.
- GO ausschließlich für den standardmäßig inaktiven Integrationspfad mit
  P0 = 0 und P1 = 0. Windows, Packaging, Notarisierung, reale
  Power-Loss-Abnahme und Produktfreigabe bleiben P2 beziehungsweise NO-GO.

## Security Sprint 10 - isolierte verschlüsselte Dokumentablage

### Architecture

- Eigenes versioniertes Dokumentcontainerformat auf Basis von libsodium
  Secretstream XChaCha20-Poly1305 ausgewählt; Backupformat und
  Backup-Domainen bleiben vollständig getrennt.
- Zufälligen 256-Bit-Document-Key pro Dokumentgeneration,
  HKDF-SHA-256-zweckgetrennten Document-Wrapping-Key und integriertes
  AES-256-GCM-Envelope mit getrenntem unveränderlichem Payload-Binding
  festgelegt.
- Opaque Storage-ID, verschlüsseltes Metadatenmanifest, unveränderliche
  Generationen, No-Clobber-Publikation, DMK-Rewrap ohne Datenrotation und
  getrennte vollständige Document-Key-Rotation definiert.

### Added

- Isolierten synthetischen Writer, Header-Inspector, read-only Verifier,
  zweiphasigen sequenziellen Reader, bewussten Testexport,
  Generationsaustausch-/Rewrap-Prototyp und Retained-/GC-Dry-Run ergänzt.
- Bewussten Testexport per atomarem No-Clobber-Rename veröffentlicht; bei
  normalen Fehlern den Inhalt nur über den offenen eigenen FD geleert und
  harte Abbrüche vor dem Commitpunkt als nicht erfolgreichen Retained-Stand
  im isolierten Exportroot abgegrenzt.
- Manipulation, falsche Identitäten/Generationen/Schlüssel, Trunkierung,
  Zusatzdaten, Chunkfehler, Symlinks, Traversal, Zielkonflikte,
  Identitätswechsel und echte Prozessabbrüche fail-closed abgedeckt.

### Tests

- 73 Sprint-10-Fokus- und Crash-Tests grün; darunter 21 echte
  Subprozessabbrüche an Writer-, Export- und Generationsgrenzen.
- Gesamtsuite: 1595 bestanden, 20 übersprungen, 67 Subtests bestanden;
  `compileall`, `pip check`, `git diff --check`, Produktimport-Isolation sowie
  lokale Secret-, Artefakt- und Klartextscans bestanden.

### Boundaries

- Keine Änderung oder Aktivierung von Produktimport, Produktviewer/-export,
  bestehendem Dokumentmodell, Startup, Login, UI, Application Services,
  Backup/Restore, Identity-VFS, Packaging, Pilot, RC, Appcast, Release oder
  Excel.
- Secretstream v1 ist sequenziell; Random Access, vollständige Replaypolicy,
  produktive Pointer-/Lifecyclepersistenz, Windows/Packaging und reale
  Power-Loss-Abnahme bleiben Folge-Gates.
- P0 = 0 und P1 = 0 im isolierten synthetischen Sprint-10-Pfad.
  Produktintegration bleibt ausdrücklich NO-GO.


## Security Sprint 9 - isolierter verschlüsselter Backupcontainer

- Isolierte synthetische Foundation für versionierte, authentifizierte Backupcontainer ergänzt.
- Ein zufälliger Backup-Key je Container wird über DMK, HKDF-zweckgetrennten
  Backup-Wrapping-Key und ein AES-256-GCM-Envelope geschützt.
- Writer, Verifier und Restore-Prototyp nutzen Secretstream XChaCha20-Poly1305;
  Produkt-Backup, `.jkmbackup`-Pfad, Startup, UI, RC und Pilot bleiben unverändert.
- Offene Folge-Gates: Packaging, Windows, realer Power-Loss, Same-User-ABA,
  Retained-GC und weitergehende Zeroization.

## Security Sprint 8 - vereinfachter synthetischer Migrationsorchestrator

### Added

- VFS-freien Crossbinding-v2- und read-only Preflight-v2-Vertrag fuer feste
  Source-/Backup-/Target-Rollen im injizierten privaten Test-Root implementiert.
- Byte-identischen Backupvertrag nach Close/WAL-Ruhe, separaten SQLCipher-
  Transfer ohne `ATTACH`, vollstaendige Snapshot-/PRAGMA-/Integritaetspruefung,
  Reopen, authentisiertes Journal/Replay-Anker-Protokoll, Neustart-Recovery und
  ausschliesslich simulierten atomaren Austausch implementiert.
- Zehn zentrale Abbruchfenster mit echten Prozessen sowie ENOSPC-, Rechte-,
  `fsync`-, `os.replace`-, Journalmanipulations-, Replay-, Artefakttausch- und
  Fremdartefaktfaelle fail-closed beziehungsweise recoverbar getestet.

### Tests

- 55 neue Sprint-8-Tests, 272 Security-Sprint-2-bis-6-Tests, 168
  Migration-State-/Sprint-8-Tests, 97 Security-Core-/Startup-/UI-Tests, 315
  Security-/Migration-State-Regressionen, 140 Support-/Sprint-8-Regressionen,
  130 Backup-/Restore-Regressionen und 29 Startup-Import-Isolationstests gruen.
- Gesamtsuite: 1431 bestanden, 20 uebersprungen, 67 Subtests bestanden;
  `compileall`, `pip check` und `git diff --check` bestanden.

### Boundaries

- Keine Produkt-, Startup-, UI-, RuntimePath-, Backup/Restore-, Pilot-, RC-,
  Release-, Identity-VFS- oder Excel-Aktivierung.
- P0 = 0 und P1 = 0 fuer den isolierten synthetischen Pfad. Reale
  Produktpfade, Windows, Packaging und produktiver Austausch bleiben P2/
  Folge-Sprints.

## Security Sprint 7B - Migration State Foundations

### Added

- Vollständigen kanonischen Migrations-Crossbinding-Kontext für Installation,
  Datenbankkontext, Migration, Schlüsselgenerationen, Registry, Journal,
  Replay-Anker, Lockkettenkopf, Dateirollen und Versionen ergänzt.
- HMAC-authentisierte append-only Locktransitionen mit Vorgängerdigest,
  monotoner Sequenz, Owner-Kontinuität und replaygebundener Evidenz ergänzt.
- Deterministische read-only Preflight-Ableitung für `NEW`, `RESUME`,
  `RECOVERY`, `COMPLETED` und `BLOCKED` aus authentisierten Projektionen
  ergänzt.

### Security review

- Tail-Replay verlangt einen extern erwarteten Lockkettenkopf samt Sequenz;
  manipulierte, entfernte, eingefügte und zurückgespielte Einträge blockieren.
- Journalphase und Locktransition sind keine frei wählbaren Preflight-Eingaben.
- Der vollständige Kontext bindet den echten Lockkopf; der Lockeintrag bindet
  über einen nicht zirkulären Digest alle übrigen Kontextfelder.

### Boundaries

- Keine Orchestrator-, Produkt-, Startup-, Login-, UI-, Backup/Restore- oder
  Migrationsverkabelung und keine Aktivierung nachgelagerter Security-Sprints.

## Security Sprint 6 - Governance für Replay-Anker, Lock und Prototype-Recovery

### Added

- Isolierte Sprint-6-Entwicklungsgrenze für externen monotonen Replay-Anker,
  exklusiven Migrations-Lock und ausführende, identitätsgebundene Recovery im
  synthetischen temporären Test-Root ergänzt.
- Anchor-, Lock- und Recovery-Namen, macOS-Keychain-Service,
  `database-migration-v1.lock`, technische Datenquellen, Lifecycles und
  Ownership registriert.
- Replay-Angreifermodell, Lock-/Stale-Regeln, Crash-/ENOSPC-/Rechteverhalten,
  verbleibende Power-Loss-/Quarantänegrenzen und Windows-DPAPI-/Dateisystemgates in
  ADR-081 bis ADR-083 dokumentiert.
- Committed/pending Cross-Store-Protokoll für Anchor-Prepare, externe
  Registry-/Journalpublikation, Digest-exakten Commit und monotones Abort nach
  Crash festgelegt; der exklusive Lock serialisiert den Advance.
- `MigrationLockPort`, `ExclusiveMigrationLock`, `InMemoryMigrationLock` und
  `UnsupportedMigrationLock` sowie die monotone Anchor-Operation
  `abort_pending(expected, observed_committed)` implementiert.
- Ausführende Prototype-Recovery mit identitätsgebundenem Rollback,
  Validierungs-/Reopen-Fortsetzung und idempotenter terminaler Verschiebung von
  evidence-gebundenem Ziel und Backup per atomarem No-Clobber-Rename in retained Quarantine ergänzt; Recovery
  löscht diese Bestände nicht. Quelle, Anchor, Registry, Journal, Lock und
  unbekannte Dateien bleiben erhalten.
- Recovery zusätzlich hart an temporären Root und Synthetik-Guard gebunden;
  ein konkurrierend angelegter fremder Quarantänepfad wird nie überschrieben.
- Prozessstartidentitäten prozessübergreifend vergleichbar gemacht und
  Stale-Takeover unter dem Kernel-Lock an einen expliziten erfolgreichen
  Recovery-Evidence-Validator für Journal-/Anchor-Nachweise gebunden.
- Kontrollierten ad-hoc-signierten Einzelpilot ohne Developer ID und den davon
  getrennten späteren Developer-ID-/Notarisierungs- beziehungsweise MDM-Pfad
  beschrieben.

### Boundaries

- Keine UI, keine Startup-, RuntimePaths-, Login-, Passwortwechsel-,
  Auth-Recovery-Code-, Touch-ID-, Support-Reset-, produktive Backup/Restore-,
  Produktmigrations-, Pilot-, Appcast- oder Releaseaktivierung.
- Security Sprint 7A ist nicht Bestandteil dieses Commits; Security Sprint 8A
  ist nicht begonnen und bleibt gesperrt.
- RC `0.2.2`, fachliche SQLite, `security.sqlite`, Pilot-/Laura-Artefakte und
  bekannte Exceldatei bleiben außerhalb der Sprint-6-Foundation.

### Gate

- Den im Schlussreview reproduzierten P1 behoben: Recovery führt für Ziel und
  Backup kein pathname-basiertes `unlink` oder `remove` mehr aus, sondern
  belässt exakt evidence-gebundene Artefakte in retained Quarantine. Das
  frühere finale Unlink-TOCTOU besteht damit nicht mehr.
- Drei im selektiven Gesamtreview reproduzierte P1 zusätzlich behoben:
  Quarantäne-Namen verwenden atomare No-Clobber-Semantik, lebende Owner werden
  bei nicht vergleichbarer Prozessidentität fail-closed blockiert, und eine
  Stale-Übernahme ist ohne erfolgreiche Recovery-Evidence-Prüfung unmöglich.
- Post-Fix-Gate vollständig grün: 215 fokussierte Sprint-6-Tests, 265
  fokussierte Tests der Security Sprints 2 bis 6, 465 Security-/Support- und
  130 Backup-/Restore-Regressionstests sowie 1148 Tests plus 67 Subtests der
  Gesamtsuite. `compileall`, `pip check`, `git diff --check`, native Bridge-
  Checks mit ausschließlich Deprecated-Warnungen und Hashprüfungen bestanden;
  P0 = 0 und P1 = 0.
- Bekannte P2-Grenze ist retained Quarantine ohne freigegebenen handlebasierten
  Bereinigungsprozess.
- Aus dem grünen Post-Fix-Gate folgt keine Produktfreigabe. Security Sprint 7A
  ist nicht Bestandteil dieses Commits; Security Sprint 8A bleibt gesperrt.

## Security Sprint 5 - Product-Key-Envelope und Migrationsjournal-Foundation

### Added

- HKDF-SHA-256-Domain-Separation für den flüchtigen Database-Wrapping-Key und
  einen getrennten Migration-Journal-HMAC-Key ergänzt.
- Zufälligen 256-Bit-Database-Key, strikt versioniertes AES-256-GCM-Envelope,
  vollständige Metadaten-AAD, monotone Rewrap-Revision und fail-closed
  Lifecycle mit persistentem Generations-High-Water-Mark
  implementiert.
- Eigene atomare Envelope-Registry außerhalb von fachlicher SQLite,
  `security.sqlite`, Keyset-Sidecar und Journal ergänzt; komplette Registry
  einschließlich leerem High-Water-Zustand per eigener HKDF-Domain und
  HMAC-SHA-256 authentifiziert.
- Kanonisches HMAC-SHA-256-Migrationsjournal mit vollständiger
  Transition-Historie, expliziter Zustandsmaschine, rollenbasierten
  Dateiidentitäten und reiner Recovery-Entscheidung ergänzt.
- Den guarded synthetischen Sprint-4-Prototyp isoliert mit Envelope und Journal
  verbunden und Abbrüche nach Backup, während/nach Export, während Validierung
  sowie nach Neuöffnung nachgewiesen.

### Security

- Unbekannte Versionen/Algorithmen, falscher DMK, AAD-/Nonce-/Ciphertext-
  Manipulation, Journal-HMAC-Fehler, Korruption, Temp-Reste, illegale
  Übergänge und Dateiabweichungen werden ohne Neuerzeugung blockiert.
- Database-Key, Wrapping-Key, Journal-Key, DMK und App-Passwort erscheinen
  weder in Journal/Metadaten noch in Logs oder Exceptions. Jeder
  Lifecycle-Rewrap verwendet einen revisionsverschiedenen HKDF-Kontext und
  eine neue zufällige Nonce.
- Journal und Envelope werden nach Authentisierung über Database-Context sowie
  Database-Key-ID/-Generation kreuzgebunden; gültige fremde Paare blockieren.
- Reservierte Pflichtchecks sind an ihre tatsächlich erreichte Journalphase
  gebunden; unbekannte oder vorzeitig behauptete Checks und rückläufige
  Zeitpunkte werden abgelehnt.
- Recovery entscheidet nur; sie führt weder produktiven Austausch noch
  Löschung einer Klartextquelle oder unbekannten Datei aus.

### Boundaries

- Keine Startup-, Login-, Passwort-, UI-, Recovery-Code-, Support-Reset-,
  Backup/Restore-, Dokument-, Produktdaten-, Pilot-, Appcast-, Packaging- oder
  Releaseintegration. Normales SQLite bleibt Produktstandard.
- RC `0.2.2`, `security.sqlite`, fachliche SQLite, Pilot-/Laura-Artefakte und
  bekannte Exceldatei bleiben unverändert. Ein Commit ist erst nach dem
  separaten Gesamtreview der Security Sprints 2 bis 5 zulässig.

### Open Gates

- Replay-Schutz durch externen monotonen Anker, produktive Database-Context-Bindung,
  Windows-DPAPI/ACL/File-ID/Reparse-Point-Port, macOS-Full-Durability,
  SQLCipher-4.17.0-Supply-Chain, Packaging/Signierung und reale Crashabnahme
  bleiben offen.

### Gesamtreview

- Fokussierte Sprintmatrix nach Reviewkorrekturen: Sprint 2 mit 46, Sprint 3
  mit 20, Sprint 4 mit 21 und Sprint 5 mit 68 bestandenen Tests.
- Vollständige Security-Regression mit 276, Backup/Restore mit 130 und
  Support-Reset mit 75 bestandenen Tests.
- Gesamtsuite mit 1020 Tests und 67 Subtests bestanden; `compileall`,
  `pip check`, `git diff --check`, Hash- und Artefaktprüfungen erfolgreich.

## Security Sprint 4 - isolierter SQLCipher-Migrationsprototyp

### Added

- Vollständig getrennten, Qt-freien Klartext-SQLite-zu-SQLCipher-Prototyp unter
  `prototypes/database_encryption_migration/` ergänzt. Er akzeptiert nur eine
  technisch markierte synthetische Fixture in einem temporären Arbeitsbereich.
- Deterministische synthetische Testquelle mit 11 eigenen Tabellen, Primär- und
  Fremdschlüsseln, Trigger, Views, expliziten Indizes, Schülern,
  Beobachtungen, Kompetenzen, Berichten, Dokumentverweisen und Binäranhängen
  ergänzt.
- Verifiziertes SQLite-Backup, separaten `sqlcipher_export`-Transfer,
  Schema-/Objekt-/Zeilen-/Wert-/Hash-/PRAGMA-Vergleich, Cipher-/SQLite-
  Integrität, Neuöffnen und Quell-Dateihashkontrolle implementiert.
- Fehlerproben für Backup, Export, Commit, Exportabbruch, Zielkorruption,
  falschen Schlüssel, Quellkorruption und falsche SQLCipher-Version sowie eine
  rein beschreibende atomare Austauschsimulation ergänzt.

### Security

- Der Prototyp erzeugt einen zufälligen 32-Byte-Database-Key ausschließlich
  zur Laufzeit. Er verwendet weder DMK noch App-Passwort und persistiert oder
  protokolliert kein Schlüsselmaterial.
- Die spätere Hierarchie bleibt `DMK -> zweckgebundener Database-Wrapping-Key
  -> zufälliger Database-Key`; DMK und SQLCipher-Key sind ausdrücklich nicht
  identisch. Wrapping und produktive Persistenz sind nicht implementiert.
- Bei jedem simulierten Fehler bleibt die Klartextquelle bytegleich. Ein
  angelegtes Cipher-Ziel wird nur bei unveränderter Dateiidentität entfernt;
  nach erfolgreichem Backup bleibt das verifizierte Backup erhalten.
- Der Vollvergleich bindet zusätzlich `sqlite_sequence`, damit die
  AUTOINCREMENT-Fortsetzung nicht unbemerkt abweichen kann.
- Ein eigenes Backup, das die nachgelagerte Vollprüfung nicht besteht, wird nur
  bei unveränderter Dateiidentität entfernt und nicht als verifiziert belassen.

### Performance

- Ein lokaler synthetischer Referenzlauf am 2026-07-22 über 12 validierte
  Tabellen und 50.062 Zeilen einschließlich `sqlite_sequence` maß 4.739.072
  Byte für Quelle/Backup, 4.583.424 Byte für das Cipher-Ziel, 0,123 s
  Quellintegrität, 0,143 s Backup, 0,057 s Export, 0,169 s Vergleich, 0,074 s
  Neuöffnen und 0,586 s Gesamtdauer. Das ist kein Produktbenchmark.

### Boundaries

- Keine Startup-, Login-, Recovery-, Touch-ID-, Support-Reset-,
  Backup/Restore-, UI-, Produktdaten-, `security.sqlite`-, Release-, Appcast-
  oder Pilotintegration. Kein Dateiaustausch und keine Klartextlöschung.
- RC `0.2.2`, Pilotdaten, bekannte Excel-Datei und produktive SQLite werden
  durch den Prototyp nicht geöffnet oder verändert. Der gemeinsame Commit ist
  an ein separates Gesamtreview gebunden.

## Security Sprint 3 - SQLCipher Infrastructure ohne produktive Migration

### Added

- Explizite Qt-freie Datenbank-Engine-Grenze mit unverändertem Standard-SQLite
  und separat konstruiertem SQLCipher-Provider ergänzt.
- Fail-closed Fehlerklassen für fehlende Engine, inkompatible Version,
  fehlendes/ungültiges Keymaterial, nicht authentisierbaren Key/Header,
  Korruption, Klartextformat und ungültige Engine-Konfiguration eingeführt.
- Isolierten Smoke und Testmatrix für verschlüsselte temporäre Datenbanken,
  Transaktionen, Integrität, Klartext-Ablehnung und synthetische Daten ergänzt.

### Security

- Keine Umgebungsumschaltung und kein Rückfall auf normales SQLite; bestehende
  Dateien werden bei Key-, Format- oder Integritätsfehlern weder überschrieben
  noch als leere Datenbank neu angelegt.
- Testkeys entstehen nur zur Laufzeit, werden nicht persistiert oder geloggt
  und sind weder App-Passwort noch DMK. Eine spätere Produktarchitektur braucht
  einen eigenen zufälligen DB-Key unter DMK-Wrapping.
- SQLCipher- und SQLite-Integrität, Foreign Keys, Cipherstatus, Headerpolicy,
  Memory-/Temp-/Journal-/Sync-Regeln und exakte Spike-Version werden geprüft.

### Packaging

- `sqlcipher3` 0.6.2 mit nachgewiesener SQLCipher Community 4.12.0 auf
  macOS arm64/Python 3.14 isoliert aufgenommen.
- Separater 13-MB-PyInstaller-Onefile-Prototyp enthält die Cipher-Extension,
  ist arm64, lokal ad-hoc-signiert und besteht den technischen Smoke.
- Dieser lokale Packaging-Nachweis besitzt im Repository noch keine eigene
  reproduzierbare Spec, Buildanweisung oder Manifestkette und ist kein
  Produkt-Packaging-Beleg.
- Dynamisch geladenes Binding, native Extension und Lizenzdaten müssen in
  PyInstaller explizit gesammelt werden; der unvollständige Prototyp schlug
  erwartungsgemäß fail-closed statt auf Standard-SQLite zurückzufallen.
- Produktziel SQLCipher 4.17.0, kontrollierte Wheels, Developer-ID,
  Notarisierung, DMG, Update-ZIP, Notices und Windows bleiben offene Gates.

### Verified

- 195 fokussierte SQLCipher-/SQLite-/Backup-/Restore-Tests bestanden.
- Vollständige Security-Regression mit 187 Tests bestanden.
- Gesamtsuite mit 929 Tests und 67 Subtests bestanden; keine gesammelten Tests
  wurden im nachgewiesenen macOS-arm64-Lauf übersprungen.
- Finaler arm64-PyInstaller-Smoke, `compileall`, `pip check` und
  `git diff --check` bestanden.

### Not Changed

- Keine Migration, Startup-/Login-/UI-/Recovery-/Support-Reset-Integration,
  Dokument- oder Backupverschlüsselung und keine Änderung am produktiven
  Backup-/Restorepfad.
- RC `0.2.2`, Pilotdaten, `security.sqlite`, fachliche Datenbank und Appcast
  bleiben unangetastet. Die bereits vor Sprintbeginn vorhandene Änderung der
  bekannten Pilottest-Exceldatei wird unverändert bewahrt. Der gemeinsame
  Commit ist an ein separates Gesamtreview gebunden.

## Security Sprint 2 - Key Foundation und Data Master Key Lifecycle

### Added

- Qt-freies Keyset- und DMK-Lifecycle-Modell mit `pending`, `active`, `revoked`
  und `failed`, 256-Bit-Zufallsschlüsseln und SHA-256-Fingerprintprüfung.
- Eigenen macOS-Keychain-Adapter mit getrenntem Service-Namespace sowie
  plattformneutralen Port für eine spätere Windows-DPAPI-/Credential-Manager-
  Implementierung ergänzt.
- Kanonisches, versioniertes Envelope-Format für bereits geschütztes
  Schlüsselmaterial und einen isolierten Metadaten-Sidecar ohne DMK-Payload
  eingeführt.

### Security

- App-Passwort und DMK vollständig getrennt; Passwortwechsel verändert weder
  Key-ID, Generation, Fingerprint noch Schlüsselmaterial.
- Falsche Bindung, Zugriffssperre, Plattformfehler, beschädigte Einträge,
  Neustartfortsetzung und wiederholbare Löschung schlagen strukturiert und
  ohne Secret-Inhalte fehl.
- Uneindeutige Längen-/Fingerprint-Korruption markiert Metadaten fail-closed,
  löscht den möglicherweise korrekten Plattform-DMK aber nicht automatisch.
- Den DMK-Keychain-Adapter in ein eigenes Infrastrukturmodul getrennt, damit
  der normale Security-Startup die Verschlüsselungs-Foundations nicht importiert.
- DMK wird weder geloggt noch an SQLite übergeben; Python-Buffers werden im
  Erzeugungspfad bestmöglich überschrieben.

### Verified

- 16 fokussierte DMK-/Keychain-/Envelope-Tests bestanden.
- Vollständige Testsuite mit 909 Tests und 67 Subtests bestanden.

### Not Changed

- Release Candidate `0.2.2`, Pilotdaten, `security.sqlite` v3, fachliche
  Datenbank, Dokumente, Backups, UI, Startup und Releasepfad bleiben
  unverändert. Keine Migration, kein SQLCipher und keine Produktaktivierung.

## Technische Voranalyse - Integrierte Verschlüsselung und Support-Reset v2

- Den bestätigten Klartext-Ist-Zustand von fachlicher SQLite-Datenbank,
  verwalteten Dokumenten, PDF-Artefakten, Backup v1 sowie Restore-Staging und
  die bestehende Security-/Keychain-/Startarchitektur dokumentiert.
- Zielarchitektur für SQLCipher, plattformgeschützten Datenhauptschlüssel,
  authentifizierte Dokument- und Backupcontainer, Klartextmigration und einen
  registrierungsgebundenen dateibasierten Support-Reset einschließlich
  Geheimwort-Updatebestätigung voranalysiert.
- Bedrohungsmodell, Schlüsselhierarchie, Protokollformate, Modul-/Schemafolgen,
  Testmatrix, Packaging-/Lizenzrisiken, Umsetzungssprints und harte
  Stopbedingungen als nicht implementierte Entscheidungsgrundlage festgehalten.
- Keine Produkt-, Schema-, Security-, Runtime-, Build- oder Teständerung; keine
  Freigabe zur Implementierung.

## Sprint 0.2S.1 - Support-Assistent UX

- macOS-Bundlemetadaten des Support-Assistenten auf Produktversion `0.2.2`,
  Release-Build `202` und Mindestversion macOS 13 festgelegt und in der
  Paketprüfung verbindlich abgesichert.
- Eigenständige grafische macOS-arm64-Betreiberanwendung für das Öffnen,
  verständliche Prüfen und Signieren einer bewusst gewählten
  `.jkmresetrequest` ergänzt.
- Flüchtigen Installationsnamen, nicht sicherheitsrelevante lesbare
  Anfragecode-Referenz, gekürzte Installationskennung sowie sichtbaren aktiven
  Supportschlüssel und gekürzten Fingerprint festgelegt.
- Bewusste Ausgabe per Zwischenablage oder exklusiver Token-Datei und minimales
  lokales Audit ausschließlich aus Zeitpunkt, Request-ID, Key-ID und Aktion
  umgesetzt.
- Request-/Tokenprotokoll, Kryptografie, Schlüsselmodell, Backupvertrag,
  Kompetenzmanager-App, Fach- und Security-Daten bleiben unverändert; kein
  privater Schlüssel, keine Passphrase und keine Runtime-Daten im Paket.

## Version 0.2.2 - Erstes beaufsichtigtes Sparkle-Pilotupdate

- Den vom Product Owner bestätigten öffentlichen Ed25519-Descriptor
  `support-2026-b` in der versionierten Produktivregistry aktiviert; privater
  Schlüssel und Passphrase bleiben getrennt außerhalb von Repository, App und
  Release-Artefakten.
- Produktversion und monotone Bundle-Buildnummer auf `0.2.2` / `202` angehoben
  und Release-Dokumentation, Pilot-Appcast sowie Build-Inventar auf das erste
  beaufsichtigte Sparkle-Update vorbereitet.
- Recovery-Code als bevorzugten ersten Weg und Support-Reset als betreuten
  Ausnahmeweg dokumentiert. Reset-Anfragen enthalten keine Schülerdaten; das
  neue Passwort setzt weiterhin die Lehrkraft selbst.
- Keine Fachfunktion, Fach- oder Security-Store-Migration, UI-Neuentwicklung,
  Bundle-ID-, Plattform- oder Kanaländerung. Stable bleibt deaktiviert;
  Developer-ID-Signierung und Apple-Notarisierung werden nicht behauptet.

## Version 0.2.1 - Beaufsichtigte Pilot-Updater-Basis

- Sparkle 2.9.4 mit fest geprüftem SHA-256, öffentlichem Pilot-EdDSA-Schlüssel,
  kleiner nativer C-ABI-Bridge und vollständiger Einbettung ins arm64-App-Bundle
  ergänzt; Python, Qt, SQLite und Sparkle werden nicht separat installiert.
- `Einstellungen > Updates` mit fester Kanalprojektion `Pilot` und ausschließlich
  bewusster Aktion `Nach Updates suchen` ergänzt. Automatische Prüfung,
  Hintergrunddownload und unbeaufsichtigte Installation bleiben aus.
- Signierter Pilot-Appcast über GitHub Pages und signiertes App-Archiv als
  getrenntes GitHub-Release-Asset vorgesehen; `stable` bleibt deaktiviert.
- Pilotbuild um den sechsten Schritt `Pilottest mit Beispieldaten fortsetzen`
  ergänzt. Er öffnet ausschließlich den vorhandenen Restore-Dialog und sucht,
  wählt oder importiert keine Datei automatisch.
- Version und monotone Bundle-Buildnummer auf `0.2.1` / `201` angehoben; Bundle-ID,
  macOS-13-Grenze, Fachschema, Securityschema und Runtime-Pfade bleiben gleich.
- Die produktive Support-Key-Registry bleibt in `0.2.1` leer. `0.2.2` ist als
  erstes beaufsichtigtes Update mit gesondert freigegebenem öffentlichen
  Support-Reset-Schlüssel vorgesehen.
- Ad-hoc-Signierung und fehlende Apple-Notarisierung bleiben ausdrücklich
  Pilotgrenzen; ein Stable-/Regelbetrieb ist nicht freigegeben.

## Sprint 0.2B.6 - Produktives Support-Reset-Werkzeug für macOS

### Added

- Zwei getrennte Finder-Starter für den geführten Offline-Signaturprozess und
  die bewusste externe, ausschließlich verschlüsselte PKCS#8-
  Schlüsselbereitstellung ergänzt.
- Versionierte, strikt validierte Produktiv-Public-Key-Registry mit
  Rotation, Retirement und Widerruf per App-Release sowie Fingerprintbindung
  ergänzt; sie bleibt ohne PO-Schlüssel leer und fail-closed.
- Separaten macOS-arm64-Supportpaket-Build mit fester Allowliste,
  Prüfsummen, Versionsinformation, Betriebsanleitung sowie Secret-, Pfad- und
  Paketscan ergänzt.

### Security

- Support-Werkzeug verarbeitet ausschließlich technische Anfragen, gibt keine
  Passphrase als Argument oder Umgebung weiter, begrenzt Entsperrversuche und
  Tokenlaufzeiten und überschreibt keine Ausgabedatei.
- App, DMG, Pilot-/Laura-Paket, fachliche Datenbank, Backups, Dokumente,
  Schülerdaten, private/Testschlüssel, Recovery-Codes und erzeugte Anfragen oder
  Tokens bleiben aus dem Supportpaket ausgeschlossen.

### Not Changed

- Keine neue Kryptografie, kein Masterkennwort, keine Cloud-/E-Mail-/
  Telemetriefunktion, keine fachliche Daten-, Schema- oder UI-Änderung. Ohne
  bereitgestellten öffentlichen Produktivschlüssel bleibt der App-Reset nicht
  produktiv freigeschaltet. Kein Commit.

## Version 0.2.0 - Release-Artefakte nach Brand Color Harmonization

### Changed

- Die Pilotübergabe in eine leere Erststartvariante und eine klar bezeichnete
  Laura-Testdatenvariante getrennt; beide enthalten dasselbe leere App-/DMG-
  Artefakt.
- Den bestehenden deterministischen Acht-Monats-Seed über den offiziellen
  SQLite-sicheren Backup-Service als separates, verifiziertes
  `Laura-Testdaten-0.2.0.jkmbackup` bereitgestellt. Security Store,
  Kontodaten, Recovery-Codes, Gerätecredentials, Tokens und Schlüssel bleiben
  ausgeschlossen.
- Paket- und Restore-Vertrag durch fokussierte Regressionstests abgesichert.
- Benutzerhandbuch, Erste Schritte, Schnellstart und Release Notes auf die
  harmonisierte Markenpalette und die klar unterscheidbaren Arbeitskontexte von
  Beobachtung, LEG und Bericht ausgerichtet.
- Vierzehn datenschutzneutrale Handbuchscreenshots auf Basis des aktuellen
  Branding-Stands erneuert.
- Der PDF-Build weist den vollständigen Pilot-Commit nun auf den Ausgabeseiten
  und in den Dokumentmetadaten aus.

### Not changed

- Keine Produktfunktion, Fachlogik, Navigation, fachliche Kurs-, Bewertungs-,
  Dokumentations- oder Feedbackfarbe geändert. Kein Commit.

## Produktplanung nach Version 0.2

### Changed

- Vision, Roadmap, Backlog, Projektstand und Sprintplanung mit dem tatsächlich
  implementierten PySide6-/SQLite-Stand des Pilot-Release-Kandidaten 0.2
  abgeglichen.
- Bereits umgesetzte Beobachtungs-, Profil-, Bericht-, LEG-, Stundenplan-,
  Stammdaten-, Backup-/Restore-, Security-, Onboarding- und Packaging-Arbeit aus
  der aktiven Zukunftsplanung entfernt und als bestätigt beziehungsweise im
  Pilottest zu validieren eingeordnet.
- Alte Excel-/VBA-Aufgaben ohne Verlust der Historie als abgeschlossen,
  historisch oder durch die PySide-/SQLite-Architektur ersetzt gekennzeichnet.
- Pilottest und befundbasierte P0-Stabilisierung als nächste Phase vorgeschlagen;
  Schülerlisten-Import, Schuljahreswechsel, Mehrkind-Schnellbeobachtung und
  Klassen-/Kursmatrix bleiben bis zur Product-Owner-Entscheidung ausdrücklich
  nicht freigegebene Planungskandidaten.

### Not changed

- Keine Produktfunktion, Fachlogik, Architektur, Persistenz, Migration, UI oder
  Tests geändert; kein Zukunftskandidat als beschlossener Implementierungssprint
  dargestellt.

## Version 0.2.0 - Pilot-Release-Kandidat

### UI-Stabilität

- Lange Aktionen in Onboarding- und Bericht-Bestätigungen gegen abgeschnittene
  Texte unter macOS gehärtet; sichere Fortsetzungsaktionen bleiben Default und
  sichtbare blaue Primäraktion.
- Beobachtungs-, Bericht- und LEG-Arbeitsfenster über eine gemeinsame
  Bildschirm- und Maximierungsregel auf die verfügbare Arbeitsfläche gelegt.
- Den LEG-Seitenwechsel ohne Stack-weiten Opazitätseffekt abgesichert, sodass
  genau eine Phase sichtbar und interaktiv bleibt, während Entwurfseingaben bei
  wiederholter Vor-/Zurücknavigation erhalten bleiben.
- Den leeren Release-Build vom erst später freigegebenen Laura-Paket getrennt;
  das ZIP entsteht nur mit dem ausdrücklichen Schalter `--with-laura-package`.

### Security

- Lokales Lehrkraftkonto, Argon2id-Passwortschutz, Recovery-Codes,
  Fehlversuchsdrosselung, sichere Startreihenfolge und flüchtige Sitzung mit
  manueller, Inaktivitäts- und Wake-Sperre als Version 0.2 zusammengeführt.
- Ausdrücklich aktivierbare Geräteanmeldung mit zufälligem macOS-Keychain-
  Geheimnis und optionaler Touch-ID-Entsperrung; das Passwort wird nicht
  gespeichert und bleibt Fallback.
- Signierten Support-Reset mit Sicherheitsbackup und
  `password_reset_pending` sichtbar abgeschlossen. Ohne freigegebenen
  öffentlichen Produktivschlüssel bleibt der produktive Ablauf deaktiviert.

### Betrieb und Dokumentation

- Backup/Restore, geführte `Erste Schritte`, optionalen Anzeigenamen,
  Dashboard-Begrüßung und Sicherheitseinstellungen in Handbuch, Handouts und
  Release-Hinweisen auf den implementierten Stand gebracht.
- Produktversion, App-Metadaten, leeren arm64-Release-Build, Dokumentnamen,
  Prüfsummen, Inventar und Laura-Übergabepaket auf `0.2.0` vereinheitlicht.

### Known limitations

- Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder
  Backups. FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen.
- Der Kandidat ist ad hoc signiert und nicht notarisiert. Echte Sleep/Wake-,
  physische Touch-ID-, App-Switcher- und vollständige reale
  Aktivierungs-/Widerrufsprüfung bleiben offen.

### Not changed

- Keine neue fachliche Funktion, Datenmigration, Verschlüsselung, Cloudfunktion,
  Produktiv- oder Privatschlüssel und keine echten Schüler- oder Pilotdaten.

## Sprint 0.2B.5 - Support-Reset-UI und vollständiger Reset-Abschluss

### Added

- Den bestehenden signierten Offline-Support-Reset als ruhigen, mehrstufigen
  Wiederherstellungsprozess in Login/Recovery und `Einstellungen > Sicherheit`
  zugänglich gemacht: technische Anfrage, bewusster Export, Tokenprüfung,
  Vorschau, verifiziertes Sicherheitsbackup und kontrollierter App-Abschluss.
- Einen rein prüfenden Application-Schritt vor der ausdrücklichen
  Resetbestätigung sowie datensparsame Desktop-Projektionen und Workerzustände
  ergänzt; Signatur-, Backup- und Security-Logik bleibt außerhalb der Widgets.

### Security

- Support-Reset bleibt kein Masterkennwort und entschlüsselt keine Daten. Anfrage
  und Token enthalten nur technische Bindungsdaten; Support erhält keine
  Schüler-, Dokument- oder Fachdaten.
- Reset setzt erst nach vollständig erzeugtem und erneut verifiziertem
  `.jkmbackup` atomar auf `password_reset_pending`, widerruft Passwort,
  Recovery-Sätze, Gerätecredentials und Sitzung und beendet anschließend die App.
- Die produktive Key Registry bleibt mangels freigegebenem öffentlichem Schlüssel
  leer. Die UI erzeugt technische Anfragen, meldet aber, dass produktiver
  Support-Reset in dieser App-Version noch nicht freigeschaltet ist.

### Not Changed

- Kein privater Supportschlüssel, Produktivschlüssel, Cloud-, Audit-, Masterpasswort-
  oder Verschlüsselungsdienst und keine fachliche Daten-/Schemaänderung.
- Echte Sleep/Wake-, Touch-ID-, App-Switcher-, Aktivierungs-/Widerrufs-,
  Developer-ID- und Notarisierungsprüfungen bleiben offen. Kein Commit.

## Sprint 0.2B.4a - Gespeicherte Geräteanmeldung, macOS-Schlüsselbund und Touch ID

### Added

- Plattformneutrale Gerätecredential-Ports und einen Security-Epoch-gebundenen
  Credential-Lebenszyklus für genau eine gespeicherte Anmeldung je lokaler
  Installation und Konto ergänzt.
- Echten, nicht synchronisierenden macOS-Schlüsselbund-Adapter für ein zufälliges
  256-Bit-Gerätegeheimnis sowie echte LocalAuthentication-Anbindung für optionales
  Touch ID ergänzt.
- Den vorhandenen Login, die opake Sperransicht und `Einstellungen > Sicherheit`
  um `Auf diesem Gerät angemeldet bleiben`, optionales Touch ID und den
  ausdrücklichen Widerruf der gespeicherten Anmeldung erweitert.
- `app-preferences.json` auf Formatversion 3 mit ausschließlich der booleschen
  Bedienpräferenz `touch_id_preferred` erweitert; Version 1 und 2 bleiben
  lesbar, Credential-ID, Hash, Salt, Secret und Security-Epoch bleiben ausgeschlossen.

### Security

- Das App-Passwort wird niemals gespeichert. Der Schlüsselbund enthält nur das
  zufällige Gerätegeheimnis; Security Store v3 enthält nur individuellen Salt,
  versionierten SHA-256-Verifikationswert, Bindungs-, Status- und Zeitmetadaten.
- Geräteanmeldung und App-Sitzung bleiben getrennt. Jede neu erzeugte Sitzung ist
  flüchtig; manuelle, Inaktivitäts- und Wake-Sperre mit 5/10/15/30/60 Minuten
  bleiben vollständig aktiv, `Nie sperren` bleibt ausgeschlossen.
- Passwortänderung, Recovery, Support-Reset, Epoch-Abweichung und Inkonsistenz
  widerrufen Credentials im Store; Schlüsselbund-Löschung erfolgt best effort.
- Touch ID ist optional, liefert keine biometrischen Rohdaten und besitzt immer
  den sichtbaren Passwort-Fallback. Nicht-macOS-Plattformen melden `unsupported`
  und bleiben vollständig im Passwortbetrieb.

### Not Changed

- Keine Verschlüsselung von Datenbank, Dokumenten oder Backups, keine
  Support-Reset-UI, Cloud-, E-Mail-, Windows-Hello-, Mehrgeräte- oder fachliche
  Funktion; fachliche Daten, IDs, Dokumentpfade, Backupformat und
  Restore-Verträge bleiben unverändert.
- Die reale physische Pilot-Mac-Abnahme von Sprint 0.2B.4, insbesondere echter
  Sleep/Wake, bleibt offen und ist keine bestandene Freigabe. Kein Commit.

## Sprint 0.2C.1 - Geführte Erste Schritte bei erster Ausführung

### Added

- Ruhige Shell-interne Ansicht `Erste Schritte` mit fünf kurzen Schritten:
  Willkommen, Arbeitsgrundlage, Kinder und Zuordnungen, erste Beobachtung sowie
  Datensicherung und Abschluss.
- Navigation aus dem Onboarding zu vorhandenen Zielen:
  `Fächer für die Dokumentation`, `Stundenplan`, `Stammdaten`, `Schüler` und
  `Datensicherung`; es werden keine Screens direkt konstruiert.
- Lokaler Onboarding-Fortschritt in `app-preferences.json` mit
  `onboarding_status`, `onboarding_current_step` und
  `onboarding_format_version`.
- Aktion `Erste Schritte erneut öffnen` in der bestehenden
  Einstellungsübersicht.

### Changed

- Das Pilot-Handout `Erste Schritte` bleibt als kompakte Pilottest-Orientierung
  eingeordnet; die verbindlichen Produkt-, Lifecycle-, Mapping- und
  Bedienverträge liegen weiterhin in den bestehenden kanonischen Quellen.
- `AppPreferencesFile` ist rueckwaertskompatibel zu Formatversion 1 und liest
  unbekannte neuere Preference-/Onboarding-Versionen konservativ ohne
  App-Absturz.
- Passwortwechsel, Recovery, Support-Reset und fachliches Restore bleiben vom
  Onboarding-Status getrennt; der Store bleibt ausserhalb von Security Store,
  fachlicher SQLite und `.jkmbackup`.
- Der Packaged-Smoke oeffnet das Onboarding nicht automatisch.

### Verified

- Neue Onboarding-/Preference-/Shell-Fokustests sowie betroffene
  Security-/Settings-Regressionen wurden ergänzt und erfolgreich ausgeführt.
- `git diff --check` und `compileall` waren erfolgreich.

### Not Changed

- Keine Importfunktion, keine fachliche Datenanlage, keine neue
  Stammgruppen-, Kurs-, Schüler-, Beobachtungs-, Berichts- oder LEG-Funktion.
- Keine Keychain-, Touch-ID-, Windows-Hello-, `angemeldet bleiben`-,
  Support-Reset-UI- oder Verschlüsselungsfunktion.
- Die reale Pilot-Mac-Abnahme von Sprint 0.2B.4 bleibt offen. Kein Commit.

## Sprint 0.2B.4 - Sichere Startintegration, Erstkonto, Login, Recovery, Sitzung und Sperre

### Added

- Produktives Auth-Gate mit expliziter Startzustandsmaschine, Erstkonto- und
  Legacy-Aufnahme, Login, Recovery-/Pending-Abschluss und fail-closed
  Fehleransichten.
- Epoch-gebundene In-Memory-Sitzung sowie zentrale manuelle, Inaktivitaets- und
  Wake-Sperre mit opaker neutraler Ansicht und Erhalt ungespeicherter Eingaben.
- Sicherheits-Unterseite fuer feste Sperrintervalle, Passwortwechsel,
  Recovery-Code-Erneuerung, `Jetzt sperren`, Verschluesselungsgrenze und
  FileVault-Hinweis.
- Optionalen lokalen Anzeigenamen bei Erstkonto und Legacy-Aufnahme,
  `Persönliche Begrüßung` in den Einstellungen und eine dezente
  Morgen-/Tag-/Abend-Begruessung auf dem Dashboard ergaenzt.

### Changed

- Runtime-Vorbereitung in technische Vor-Auth- und fachliche Nach-Auth-Phase
  geteilt; Pilotdaten, Produktordner, Logging, fachliche SQLite, Adapter,
  Projektionen und `AppShell` starten erst nach Authentifizierung.
- Recovery und Kontoaufnahme aktivieren neue Codes erst nach ausdruecklicher
  Sicherungsbestaetigung; Passwortwechsel und Reset binden Sitzungen an die
  monotone Security-Epoch.
- Backup-/Restore-UI reagiert auf Sperre, ohne laufende Backups oder bestaetigte
  Worker-Handoffs abzubrechen; Packaged-Smoke bleibt doppelt isoliert.
- Den vorhandenen atomaren lokalen Praeferenzpfad als allgemeinen
  `app-preferences.json`-Store fuer Sperrintervall und optionalen `display_name`
  ausgerichtet; kein zweiter Store und keine Security-/Fachdatenkopplung.
- Login: Enter startet Anmeldung statt versehentlich Recovery zu öffnen.

### Verified

- 800 Gesamttests mit Subtests sowie 250 fokussierte
  Profil-/Dashboard-/Security-/Backup-/Restore-Tests, `compileall` und
  Offscreen-Import erfolgreich.
- Offscreen-Start- und Sichtpruefungen fuer Erstkonto, Login, opake Sperre,
  ungespeicherte Eingaben und fail-closed Zustaende in 1180x760 und 1400x900
  erfolgreich.
- Isolierter arm64-PyInstaller-Build und Packaged-App-Smoke erfolgreich;
  normaler Paketstart bleibt am Auth-Gate, ein einzelner Smoke-Schalter wird
  fail-closed abgewiesen und das leere Bundle enthaelt keine fachliche
  Datenbank.

### Not Changed

- Keine fachliche Funktion, fachliche Datenmigration, Aenderung von IDs,
  Dokumentpfaden, Backupformat oder Restore-Vertraegen.
- Anzeigename bleibt ausserhalb von `security.sqlite`, Security-Logs,
  Support-Reset-Anfragen und `.jkmbackup`; Passwortwechsel, Recovery und Reset
  veraendern ihn nicht.
- Keine Keychain-, Touch-ID-, Windows-Hello-, `angemeldet bleiben`-,
  Support-Reset-UI- oder Verschluesselungsfunktion und kein Commit.

## Sprint 0.2B.3 - Signierter Support-Reset-Core mit Ed25519

### Added

- Qt-freien Offline-Support-Reset mit Ed25519, kanonischem `JKM-SR1`-Token und strikt gebundener technischer Reset-Anfrage umgesetzt.
- Oeffentliche Offline-Key-Registry mit Rotation/Widerruf per App-Update, monotone Security-Epoch und migrationssicheren Security-Store v2 ergaenzt.
- Vorbedingung eines erfolgreich erzeugten und vollstaendig verifizierten fachlichen `.jkmbackup` sowie atomaren Wechsel zu `password_reset_pending` angebunden.
- Getrennte Support-Werkzeuge fuer passphrasengeschuetztes PKCS#8-Keymaterial und Tokensignatur ohne Aufnahme in das App-Bundle ergaenzt.

### Changed

- `cryptography 49.0.0` samt reproduzierbaren macOS-Buildabhaengigkeiten registriert und die PyInstaller-Spezifikation um den Qt-freien Support-Reset-Core erweitert.
- Security Store v1 wird bei explizitem Security-Zugriff additiv und transaktional auf Schema v2 migriert; bestehende Accounts, Argon2id-Hashes, Recovery-Codes und Markerbindung bleiben erhalten.

### Security

- Es gibt kein Masterpasswort, keinen privaten Schluessel im Repository, Build oder App-Bundle, keinen Cloud-Dienst und keinen algorithmischen Fallback.
- Reset-Anfragen gelten hoechstens 24 Stunden; Tokens standardmaessig 30 Minuten und hoechstens zwei Stunden bei zwei Minuten Uhrtoleranz. Installation, Nutzer, Anfrage, Nonce, Aktion und `key_id` sind signiert gebunden und einmalig.
- Der Reset veraendert ausschliesslich Authentifizierungszustaende. Fachliche Datenbank, Dokumente, Backups, IDs, Backupformat und Restore-Vertraege bleiben unveraendert.

### Verified

- 43 neue Support-Reset-/Tool-Tests, 83 fokussierte Security-Tests, 128 Backup-/Restore-/Runtime-Kompatibilitaetstests sowie 767 Gesamttests und 67 Subtests erfolgreich ausgefuehrt.
- `compileall`, Offscreen-Import, realer Ed25519-Sign-/Verify-Smoke, v1-v2-Migrations-Smoke, reales verifiziertes `.jkmbackup` und `pip check` erfolgreich.
- Isolierter arm64-PyInstaller-App-Build, Packaged-App-Smoke und eigener gebuendelter Ed25519-Smoke erfolgreich; Bundle-Scan bestaetigt den Core und schliesst Support-Tools, Tests, Fixtures sowie private Schluesseldateien aus.

### Not Changed

- Keine Auth-/Reset-/Sperr-UI, Startblockade, Sitzung, App-Beendigung, neues Passwort, neue Recovery-Codes, Keychain, Touch ID, Geraete-/Sitzungstokens, Verschluesselung, Cloud oder fachliche Funktion. Kein Commit.

## Sprint 0.2B.2 - Security Core

### Added

- Eigenstaendigen Domain-/Application-/Infrastructure-Security-Core mit separatem versioniertem SQLite Store, fail-closed Enrollment-Marker und restriktiven Runtime-Dateirechten ergaenzt.
- Argon2id-Passworthashing, unveraendernde Passwort-Policy, persistente Fehlversuchsdrosselung, zufaellige Installations-/Nutzer-IDs und lokales Ein-Konto-Modell umgesetzt.
- Zehn einmalige lokal gesalzene und gehashte Recovery-Codes je Satz sowie crash-sichere zweiphasige Regeneration umgesetzt.
- Explizite Security-Ausschluesse fuer bestehende Backup-, Restore-, Export- und Diagnosegrenzen sowie umfassende Core-/Kompatibilitaetstests ergaenzt.

### Security

- Die Anwendungssperre ist keine Verschluesselung der Datenbank, Dokumente oder Backups; direkter lokaler Dateizugriff bleibt ein dokumentiertes Restrisiko.
- Store-/Marker-Widersprueche, Korruption und unbekannte neuere Versionen werden fail-closed behandelt. Passwortverlust loescht oder migriert keine fachlichen Daten.
- Argon2id-Time-Cost nach realer Pilot-Mac-Kalibrierung von 3 auf 6 erhoeht; Memory 65536 KiB, Parallelism 1, Salt 16 Byte, Hash 32 Byte sowie Schema- und Hashformatversion 1 bleiben unveraendert. Time-Cost-3-PHC-Hashes bleiben pruefbar und werden nur nach erfolgreicher Anmeldung aktualisiert.

### Verified

- 40 fokussierte Security-Core-Tests sowie 724 Gesamttests und 67 Subtests erfolgreich ausgefuehrt; Crashpunkte, Uhrmanipulation, Parallelzugriff, Geheimnisschutz und Backup-/Restore-Ausschluesse sind abgedeckt.
- `compileall`, Offscreen-Import, realer Argon2id-Hash-/Verify-Smoke sowie isolierter arm64-PyInstaller-Build mit vorhandenem Packaged-App-Smoke erfolgreich.
- Kalibrierung nach je einem Aufwaermlauf und acht Messungen: Time Cost 4 `146,00 / 145,83 / 149,08 / 145,93 / 150,41 / 148,37 / 145,75 / 145,96 ms` (Mittel `147,17 ms`), Time Cost 5 `182,87 / 182,94 / 182,41 / 182,34 / 184,69 / 182,34 / 182,36 / 182,47 ms` (Mittel `182,80 ms`) und Time Cost 6 `219,66 / 219,18 / 219,30 / 221,22 / 219,21 / 220,08 / 219,71 / 219,85 ms` (Mittel `219,78 ms`).

### Not Changed

- Keine Login-, Konto-, Sperr-, Recovery- oder Passwortaenderungs-UI, keine Sitzung, keine Startblockade, keine fachliche Datenbankmigration, keine geaenderten fachlichen IDs, kein Ed25519, Support-Reset, Keychain, Cloudkonto, Rollen- oder Mehrbenutzerbetrieb. Kein Commit.

## Sprint 0.2A.4a - Asynchrone Backup-/Restore-Operationen

### Added

- Lang laufende Backup-Erstellung, Backup-Prüfung, Restore-Prüfung, Restore-Staging und Prepared-Prüfung über einen langlebigen `BackupRestoreOperationsController`, genau einen `QThread` und einen widgetfreien `QObject`-Worker aus dem Qt-Hauptthread verlagert.
- Unbestimmte technische Fortschrittsphasen, vollständige Aktions- und Navigationssperre während `running`/`finishing`, kontrollierte Close-Blockade und datensparsame Fehlerprojektion ergänzt.
- Restore-Handoff und Prozessstart bleiben im Hauptthread; die App schließt erst nach erfolgreichem einmaligem Prozessstart. Ein Startfehler lässt App und Live-Daten unverändert geöffnet und verwirft die UI-Vorschau für diesen Versuch.

### Not Changed

- Keine fachliche Funktion oder fachliche UI, keine Backup-/Restore-Core-Logik, kein automatisches Backup, kein Import, kein Passwortschutz und kein Nutzerkonto geändert oder ergänzt. Kein Commit.

## Sprint 0.2A.4 - Einstellungsnavigation und Backup-/Restore-UI

### Added

- Einstellungen als ruhige Übersicht mit den getrennten Unterseiten `Stundenplan`, `Fächer für die Dokumentation` und `Datensicherung` ergänzt.
- Manuelle Backup-Erstellung, Backup-Prüfung, datensparsame Restore-Vorschau, ausdrückliche Wiederherstellungsbestätigung und kontrollierte Worker-Übergabe über die vorhandenen technischen Services sichtbar gemacht.

### Not Changed

- Keine fachliche Funktion oder fachliche UI, keine Beobachtungs-, Kompetenz-, Dashboard-, Profil-, Bericht-, LEG-, Stundenplan-, Fachauswahl-, Stammdaten- oder Lehrplankataloglogik geändert. Keine automatische Sicherung, Aufbewahrung, Import-, Passwort- oder Nutzerkontofunktion und kein Commit.

## Sprint 0.2A.3c - Produktiver Restore, Worker, Journal, Rollback und Start-Recovery

### Added

- Governance-Vertrag fuer exklusiven Runtime-Lock, einmalige Handoff-Datei, Qt-freien Restore-Worker, persistentes technisches Journal, Live-Austausch, vollstaendigen Rollback, Start-Recovery und Startup-Handshake ergaenzt.
- Kernel-gestuetzten Runtime-Lock mit Prozessstart-Identitaet, kontrollierter Deskriptoruebergabe, einmaliger kanonischer Handoff-Datei und stabil gebundener Archivkopie umgesetzt.
- Produktiven Restore-Service mit Sicherheitsbackup, WAL-Checkpoint, komponentenweisem DB-/WAL-/SHM-/Documents-Austausch, atomarem Current-State, append-only Ereignisjournal, vollstaendigem Rollback und idempotenter Start-Recovery umgesetzt.
- Einmaligen kurzlebigen Resume-Token, read-only Startup-Verifikation und fruehen Entwickler-/Paket-Workerdispatch vor Qt- und Runtime-Initialisierung umgesetzt.

### Changed

- `main.py` erwirbt den exklusiven Instanz-Lock und fuehrt Start-Recovery beziehungsweise Restore-Handshake vor `QApplication`, Runtime-Vorbereitung, Logging und Datenbankinitialisierung aus.
- Die PyInstaller-Spezifikation bindet den Qt-freien Restore-Worker und seine Core-Services explizit in das gebuendelte Executable ein.

### Security

- Sicherheitsbackup, vollstaendige Prepared-Pruefung, V1-Kompatibilitaet, Pfad-Disjunktheit, Speicher, Schreibrechte und beendete App-Datenbankzugriffe sind zwingende Vorbedingungen des ersten Live-Renames.
- Bei jedem unsicheren Zustand hat Rollback Vorrang; ist ein konsistenter Zustand nicht beweisbar, bleibt die App mit `manual_recovery_required` geschlossen und alle technischen Beweis- und Wiederherstellungsartefakte bleiben erhalten.
- Jeder kritische Rename besitzt gefsynctes Intent und Completed; installierte Managed Files werden gegen den vor dem Austausch gehashten Prepared-Bestand geprueft, alte Komponenten gegen ihre journalisierten Groessen und SHA-256-Hashes zurueckgestellt.

### Verified

- 30 neue Lock-, Handoff-, Worker-, Journal-, WAL-/SHM-, Austausch-, Fehler-, Rollback-, Recovery- und Handshake-Tests sowie 669 Gesamttests erfolgreich ausgefuehrt.
- `compileall`, offscreen Import, temporaerer arm64-PyInstaller-Build, gebuendelter Worker-Exitcode und isolierter Packaged-App-Smoke mit PDF und verifiziertem Backup erfolgreich.

### Not Changed

- Keine fachliche Funktion, sichtbare UI, Fachdatenmigration ausserhalb des vorhandenen Stagings, Import-, Passwort-, Nutzerkonto-, Onboarding-, automatische Backup- oder Aufbewahrungsfunktion und kein Commit.

## Sprint 0.2A.3b - Restore-Staging, V0-V1-Migration, Pfad-Rebasing und Sicherheitsbackup

### Added

- Verbindliche Governance fuer ausschliesslich stagingbasiertes Restore-Preprocessing, registrierte V0-V1-Migration, technische Managed-File-Materialisierung, vorbereitetes Pfad-Rebasing und getrenntes Restore-Sicherheitsbackup ergaenzt.
- Persistente, per Restore-ID gebundene Staging-Struktur mit datensparsamem technischem State sowie getrennte Application-Schritte fuer Pruefung, Vorbereitung, Sicherheitsbackup, Prepared-Pruefung und Cleanup umgesetzt.

### Security

- Produktive SQLite-Datei und produktive `documents/` bleiben waehrend aller Staging-, Migrations-, Materialisierungs-, Rebase- und Pruefschritte unveraendert.
- Unbekannte oder neuere Schemata, Archivwechsel, Restore-ID-Kollisionen, Pfadtraversal, Symlinks, Sonderdateien sowie Hash-, Groessen-, Count-, Snapshot- oder Inventarabweichungen werden abgelehnt.

### Verified

- 26 Restore-, 17 Datenbank-Kompatibilitaets- und 61 Backup-Tests sowie 639 Gesamttests erfolgreich ausgefuehrt.
- Staging-only V0-V1-Migration, vollstaendiger Transaktionsrollback, Pfad-Rebasing, externe Referenzen, Bericht-/LEG-Snapshots und PDFs, Archivbindung, technischer State, Speicherplatz, Symlink- und Korruptionsfaelle, Cleanup und Sicherheitsbackup abgedeckt.

### Not Changed

- Keine fachliche Funktion, sichtbare UI, SQLite-Fachtabelle, Live-Migration, produktiver Austausch, Live-Rename, Worker, Instanz-Lock, Live-Rollback, Journal, Start-Recovery, App-Neustart oder Commit.

## Sprint 0.2A.3a - Datenbank-Kompatibilitaet und Restore-Verifier

### Added

- Verbindlichen, von Backupformat und App-Version unabhaengigen Datenbank-Kompatibilitaetsvertrag V1 mit `PRAGMA user_version`, registriertem vollstaendigem Schemafingerprint und bekanntem unversioniertem `c029aff`-Vorgaenger dokumentiert.
- Read-only Kompatibilitaetsinspektion, isolierte Restore-Verifikation und datensparsame technische Vorschau als allgemeine Betriebsfunktionen umgesetzt.

### Changed

- Neue schemafreie Datenbanken werden als V1 gekennzeichnet; vorhandene unversionierte Datenbanken bleiben beim normalen Start unveraendert und werden nicht automatisch adoptiert oder migriert.
- Backup-Kompatibilitaetsmetadaten werden aus dem tatsaechlich inspizierten Snapshotzustand statt allein aus einer Konstante abgeleitet; Backupformat v1 und dessen bestehender Schema-Fingerprint bleiben unveraendert.

### Verified

- 17 Kompatibilitaets-, 12 Restore- und 61 Backup-Tests sowie 625 Gesamttests erfolgreich ausgefuehrt.
- Schema-/`user_version`-Rollback, bekannte V0-Pilotdaten, vollstaendige Fingerprint-Unterschiede, Manifestwidersprueche, Integritaets-, Fremdschluessel-, Count-, Managed-File-, Datenschutz-, Temp-Bereinigungs- und Live-Unveraendertheitspfade abgedeckt.

### Not Changed

- Keine fachliche Funktion, sichtbare UI, SQLite-Fachtabelle, Migration, persistentes Restore-Staging, Pfad-Rebasing, Sicherheitsbackup, Worker, Live-Austausch, Rollback, Start-Recovery, Neustart oder Commit.

## Sprint 0.2A.2a - Backup-Sicherheitsnachpruefung

### Changed

- Exklusive Hardlink-Veroeffentlichung so gehaertet, dass ein fremder Race-Gewinner niemals geloescht oder ueberschrieben wird.
- Packaged-Smoke vor jeder Qt-/Runtime-Initialisierung an einen expliziten Marker und ein geprueftes eigenes temporaeres Smoke-Verzeichnis gebunden.
- Busy-Timeout auf die tatsaechliche zusammenhaengende Blockierungsdauer begrenzt und bei erkennbarem Snapshot-Fortschritt zurueckgesetzt.
- Verwaltete Dateien ueber einen geoeffneten `documents`-Directory-FD ohne Symlink-Folgen gelesen und Geraet/Inode zusaetzlich zu Typ, Groesse und Aenderungszeit geprueft.
- Normalisierte explizite Indexdefinitionen einschliesslich Partial-Index-`WHERE`-Praedikaten in den Schema-Fingerprint aufgenommen.
- Manifest-Buildwerte strikt auf technische Versions-, Git- und Tree-State-Werte begrenzt; Gesamtgroessenlimit auch waehrend der isolierten Extraktion durchgesetzt.
- Nicht erforderliche PyInstaller-Hidden-Imports fuer statisch erkennbare Backup-Module entfernt und den Runtime-Path-Protocol auf tatsaechlich benoetigte Pfade reduziert.

### Verified

- 60 fokussierte Backup-Tests und 595 Gesamttests erfolgreich ausgefuehrt; reale SQLite-Busy-/WAL-, Datei-/Inode-/Symlink-, Publish-, ZIP-, Datenschutz- und Fehlerbereinigungspfade sind abgedeckt.
- Fingerprint mit Python SQLite 3.50.4 und SQLite CLI 3.51.0 fuer identische Schemata verglichen; abweichende Partial-Index-Praedikate erzeugen unterschiedliche Fingerprints.
- Temporaerer PyInstaller-Testbuild ausserhalb des Repositorys ohne Backup-Hidden-Imports erfolgreich; isolierter Laura-Paket-Smoke erzeugte und verifizierte genau ein `.jkmbackup`.

## Sprint 0.2A.2 - Sicheres Backup-Backend und Integritaetspruefung

### Added

- Explizites, ZIP-basiertes `.jkmbackup` der Formatversion 1 als allgemeine Betriebsfunktion mit Core- und Application-Schicht ergaenzt.
- SQLite-Online-Snapshot ausschliesslich ueber Pythons Backup API, begrenztes Busy-Warten, `integrity_check`, `foreign_key_check` und deterministischen strukturellen Schema-Fingerprint umgesetzt.
- Striktes Inventar fuer aktive und soft-deaktivierte registrierte Dokumente sowie finale Bericht-/LEG-PDFs ergaenzt; externe Referenzen erscheinen nur als pfadfreie Summen, unregistrierte oder instabile verwaltete Dateien blockieren die Sicherung.
- Kanonisches datensparsames Manifest, sichere ZIP-Struktur, SHA-256-Pruefungen, Limits und isolierten `BackupVerifier` mit erneuter Datenbank-, Count-, Fingerprint- und Nutzdateipruefung ergaenzt.
- Packaged-App-Smoke um Backup-Erstellung und -Verifikation auf isolierten Pilotdaten erweitert; PyInstaller-Module explizit registriert.

### Pruefbasis vor Sprint 0.2A.2a

- 32 fokussierte Backup-Szenarien, macOS-Runtime-, Bericht-/LEG-PDF- und Revisionsregressionen sowie die vollstaendige Testsuite mit 563 Tests erfolgreich ausgefuehrt.
- Quell-Smoke und fiktiver Laura-Pilotdaten-Smoke erzeugten jeweils ein verifiziertes Backup ausserhalb produktiver Datenwurzeln.

### Not Changed

- Keine fachliche Funktion, sichtbare UI, SQLite-Tabelle, Schema-Migration, Restore-Funktion, automatische Sicherung, Verschluesselung, Passwort-, Nutzerkonto-, Import- oder Onboarding-Funktion.
- Das bestehende geschlossene macOS-Shell-Backup bleibt unveraendert nutzbar.

## Pilot 0.1.2 - Einrichtungsreihenfolge in den Pilotunterlagen

### Changed

- Technische Pilotversion auf `0.1.2` angehoben; App, Packaging, sichtbare Dokumentversionen und Laura-Paket beziehen die Version weiterhin aus `src/version.py`.
- Benutzerhandbuch um die verbindliche Ersteinrichtung einer leeren Anwendung ergänzt und die Reihenfolge in Stammdaten, Arbeitsabläufen, FAQ sowie Hinweisen auf Stammgruppe und Kurs vor dem Anlegen eines Kindes ausgerichtet.
- Schnellstart und Erste Schritte um den kompakten Unterschied zwischen leerer Anwendung und bereits vorbereiteten fiktiven Laura-Pilotdaten ergänzt.

### Not Changed

- Keine Produktcode-, App-UI-, Fachlogik-, Datenmodell-, SQLite-, Repository-, Service-, Adapter-, ViewModel-, Migrations- oder Testdatenänderung.

## Pilot 0.1.1 - aktualisierter Beobachtungsdialog und Releasequellen

### Changed

- Technische Pilotversion auf `0.1.1` angehoben; Packaging, Dokumentnamen und Laura-Paket beziehen die Version weiterhin aus `src/version.py`.
- Produktiven Handbuch-Screenshot des normalen Beobachtungsdialogs mit fiktiven Pilotdaten, konkreter Kompetenz, vollständiger farbiger Bewertungszeile und eindeutigem Auswahlzustand ersetzt.
- Handbuchtext um die ergänzende Orientierungsfunktion der Pastellfarben sowie die weiterhin maßgeblichen Text-, Symbol- und Auswahlzustände ergänzt; Schulnoten- oder automatische Gesamtbewertungssemantik ausdrücklich ausgeschlossen.
- Schnellstart, Erste Schritte und Backup-Anleitung als reproduzierbare, versionierte PDF-Quellen in den Dokumentbau aufgenommen und das Laura-ZIP auf eine frische Zusammenstellung der aktuellen Release-Ausgaben umgestellt.

### Not Changed

- Keine weitere App-UI, Fachlogik, Datenmodell-, SQLite-, Repository-, Service-, Adapter-, ViewModel-, Migrations- oder Testdatenänderung.
- Der Schnellbeobachtungs-Screenshot bleibt unverändert, weil dort keine Bewertungsoptionen sichtbar oder fachlich relevant sind.

## UI-Fix - Pastell-Bewertungsbadges im Beobachtungsdialog

### Changed

- Die vier textgestuetzten Bewertungsstufen im Beobachtungsdialog verwenden jetzt dieselbe zentrale `ratingToken`-Pastellvariante wie die Lernentwicklungskarten.
- Auswahl, Hover, Fokus, Pressed und Disabled sind zentral gestaltet; die aktive Stufe bleibt zusaetzlich durch Haken, Rahmen, Schriftgewicht und nativen Auswahlstatus erkennbar. Die vier Badges stehen immer in einer Reihe: bei breiter Arbeitsflaeche mit vollstaendiger Bedeutung, bei 1180 x 760 kompakt als `++`, `+`, `-`, `--`.
- Accessible Names nennen Symbol, sichtbare Bedeutung und Auswahlstatus; Maus, Enter und Leertaste bedienen weiterhin die vollstaendige Bewertungsflaeche.

### Not Changed

- Keine Aenderung an den gespeicherten Werten `--`, `-`, `+`, `++`, Bewertungs- oder Kompetenzlogik, Datenmodell, SQLite, Backend-Schichten, Speicherablauf oder Validierung.

## Sprint 8D - Laura-Pilotpaket

### Added

- Selbsterklärendes ZIP-Paket `Jenaplan-Kompetenzmanager_Pilot_0.1.0_Laura.zip` mit Startdatei, Laura-DMG, Installation, Erste-Schritte-Kurzanleitung, Benutzerhandbuch, Schnellstart, führender Pilottest-Arbeitsmappe, Backup-Anleitung, Backup-Skript und Versionsübersicht erzeugt.
- Kompakte zweitseitige Lehrkraft-PDFs für erste Testschritte, Schnellstart und technisches Pilot-Backup in der bestehenden ruhigen Pilotgestaltung ergänzt.

### Verified

- ZIP vollständig entpackt, erwartete Ordnerstruktur und verständliche Dateinamen geprüft sowie verschachtelte ZIPs, Entwicklerdateien und lose Datenbankdateien ausgeschlossen.
- Alle enthaltenen PDFs geprüft, Pilottest-Arbeitsmappe erfolgreich in Microsoft Excel geöffnet, Backup-Skript syntaktisch validiert und Laura-DMG bytegleich zum geprüften Ausgangsartefakt bestätigt.
- Paketdatenmodus mit 24 ausschließlich fiktiven Kindern, Bericht-/LEG-Revisionen und `real_student_data_included=false` erneut per Packaged-App-Smoke-Test bestätigt.

### Not Changed

- Keine Fachlogik, App-UI, Datenmodelle, Migrationen oder Produktfunktionen geändert.

## Sprint 8C - Pilotpaket UX und Installation

### Added

- Ruhiges gebrandetes DMG-Finder-Layout mit viel Weißraum, klarer Installationsrichtung, App, Programme-Verknüpfung und Lehrkraft-Installationsanleitung ergänzt.
- Lehrkraftgerechte Installationsanleitung als Markdown-Quelle und reproduzierbar erzeugtes PDF sowie gestaltetes PDF-Benutzerhandbuch mit Inhaltsverzeichnis, Seitenzahlen und Produktscreenshots ergänzt.
- Getrennte Paketvarianten `empty` für den technischen Smoke-Test und `laura` für die Übergabe mit ausdrücklich fiktiven Pilotdaten und eindeutigen DMG-Dateinamen ergänzt.
- Laura-Pilotdaten um Berichtsentwürfe, Berichtrevisionen, LEG-Entwürfe, LEG-Revisionen und finale Beispiel-PDFs über die bestehenden produktiven Schichten erweitert.

### Changed

- Benutzerhandbuch um `Installation und erster Start`, lokale Datenablage, Pilotdaten, App-Austausch und Backup-Hinweis ergänzt; Entwicklerstart, Entwicklerpfade, interne Klassenquellen und Prototypverweise aus der Lehrkraftfassung entfernt.
- Technische Installations- und Backup-Dokumentation auf das aufgeräumte DMG und die getrennt ausgelieferten Übergabeartefakte ausgerichtet.

### Not Changed

- Keine Änderung an Fachlogik, App-UI, Datenmodell, Schema, Migration oder produktiven Funktionen.
- Kein Windows-Paket, Auto-Updater, Cloudkonto, App-Store-Release oder UI-Backup-Assistent.

## macOS Pilot-Deployment 0.1.0

### Added

- Reproduzierbaren Apple-Silicon-Build mit PyInstaller, eingebetteter Python-/PySide6-/ReportLab-Laufzeit, Bundle-ID, App-Icon, macOS-13-Mindestversion und Drag-and-drop-DMG ergänzt.
- Getrennten Benutzerdatenpfad unter `~/Library/Application Support/Jenaplan-Kompetenzmanager/` mit Datenbank, Dokumenten, Exporten, Backups und Logs sowie verständlicher Startfehlermeldung ergänzt.
- Kontrollierte Pilotdatenoptionen `empty` und ausdrücklich fiktiv `laura`, automatisierten Packaged-App-Smoke-Test und technisches geschlossenes App-Backup ergänzt.
- Installations-, Gatekeeper-, Update-, Deinstallations- und Backup-Dokumentation für den Pilotbetrieb ergänzt.

### Changed

- Statische Assets und Lehrplankatalog werden in Quell- und Bundle-Ausführung über denselben Ressourcenpfad aufgelöst; der Entwicklerstart verwendet weiterhin `data/kompetenzmanager.sqlite`.
- Historische Packaging-, Produktivpfad- und Backup-Risiken in `docs/PYSIDE6_APP_FEASIBILITY.md` auf den verifizierten Pilotstand fortgeschrieben.

### Not Changed

- Keine Änderung am fachlichen Datenmodell, an Fachlogik, Berichts-/LEG-Snapshotregeln oder bestehender SQLite-Schemaarchitektur.
- Kein Windows-Paket, Auto-Updater, App-Store-Release, Cloudkonto oder UI-Backup-Assistent.

## Benutzerhandbuch – aktuelle Funktionsgrundlage

### Added

- Vollständige deutschsprachige Inhaltsgrundlage für das Benutzerhandbuch unter `docs/user_manual/USER_MANUAL_SOURCE.md` aus dem tatsächlich implementierten PySide-/SQLite-Stand ergänzt.
- Vierzehn aktuelle, visuell geprüfte Produktscreenshots mit ausschließlich fiktiven Testdaten unter `docs/user_manual/screenshots/` ergänzt.
- Produktiv umgesetzte Funktionen, Prototypen, Planungen und bewusst noch nicht verfügbare Funktionen getrennt ausgewiesen sowie ein interner Quellenanhang für die spätere fachliche Redaktion ergänzt.

### Not Changed

- Keine Produktcode-, Datenmodell-, SQLite-, Migrations- oder Teständerung.
- Kein gestaltetes Word- oder PDF-Handbuch und keine Produktfreigabe erzeugt.

## Info-Ansicht – Projektinhaber

### Changed

- Die bestehende Info-Ansicht benennt den Jenaplan-Kompetenzmanager, Jörg Gehrke als Entwickler, die vorhandene Einordnung als lokale Desktop-App, eine kurze Produktbeschreibung sowie den Copyright-Hinweis für 2026.
- Die veraltete Workbook-Version `v0.4` und der Speicherhinweis erscheinen nicht mehr als aktuelle Produktinformation.

### Not Changed

- Keine Geschäftslogik, Datenquelle, SQLite-Anbindung, Persistenz, Navigation oder andere Menüfunktion geändert.

## UI Fix - Stammdaten-Verwaltungslisten

### Changed

- Stammgruppen, Kurse und Kursverbünde als kompakte, responsive Verwaltungslisten mit ruhigen Headern, klaren Zeilenabständen sowie sichtbaren Hover-, Auswahl- und Fokuszuständen überarbeitet.
- Statuswerte als textlich eindeutige Badges und Kursfarben als dezente Kontext-Badges dargestellt; Farbe bleibt ergänzende Orientierung und nie alleinige Information.
- Kursverbünde bündeln Stammgruppen und Kurse in einer zweizeiligen Zuordnungsdarstellung; Bearbeiten bleibt über die große Zeilenfläche per Doppelklick, per Enter und über eine ausreichend breite, per Tab erreichbare Aktion verfügbar.
- Erklärende Empty States, Accessible Names, Tooltips und die Darstellung bei 1180 × 760 sowie 1400 × 900 verifiziert.

### Not Changed

- Keine Änderung an Datenmodell, SQLite, Repository, Services, Adaptern, ViewModels, Stammdaten-, Kurs- oder Persistenzlogik.
- Keine neuen Funktionen, Datenquellen, UI-Felder oder technischen Identitäten ergänzt.

## Sprint 11A - Release Documentation Alignment

### Changed

- `PROJECT.md` auf den tatsaechlich implementierten PySide-/SQLite-Produktstand nach Sprint 10B und den Schuelerprofil-UX-Fixes ausgerichtet; Excel/VBA, historische Workbook-Artefakte und fruehe Excel-Sprints klar als abgeloeste Vorstufe gekennzeichnet.
- `SPRINTS.md` ohne Entfernung von Sprintinhalten konsolidiert: produktiv umgesetzte Sprints abgeschlossen markiert, alte Commit-Statushinweise entfernt und historische Excel-/Workbook-Spikes als beendet beziehungsweise abgeloest eingeordnet.
- ADR-050 bis ADR-057 um einheitliche Umsetzungsstatus ergaenzt; bereits entschiedene Teile und verbleibende Product-Owner- beziehungsweise Betriebsfragen sichtbar getrennt.
- Changelog-Struktur fuer Sprint 10B, die beiden produktiven Schuelerprofil-UX-Fixes und diese Dokumentationsharmonisierung vorbereitet, ohne Release-Version oder Auslieferungsstatus festzulegen.

### Not Changed

- Keine Produktfunktion, Architektur, Fachlogik, Datenmodell-, SQLite-, Repository-, Service-, Adapter-, ViewModel-, UI-, Test-, Prototyp- oder Pilottestdatei geaendert.
- Keine Release-Version, kein Release-Tag und keine Auslieferungsentscheidung festgelegt.

## UI Fix - Dynamische Stundenmarkierung im Dashboard

### Changed

- Die vorhandene blaue Markierung in der Dashboard-Hero-Timeline folgt jetzt der laufenden Stunde aus der bestehenden Stundenplanprojektion; außerhalb einer Stunde bleibt sie neutral.

### Not Changed

- Keine Änderung an Stundenplanlogik, Datenmodell, Navigation, Dashboardstruktur oder sichtbaren UI-Elementen.

## UI Fix - Beobachtungsdialog-Workspacegröße

### Changed

- Beobachtungsdialog startet nun wie der vergleichbare LEG-Workspace in der großen Desktop-Arbeitsgröße 1400 × 900 und nutzt damit den verfügbaren Bildschirmbereich besser aus.

### Not Changed

- Keine Änderung an Beobachtungs-, Kompetenz-, Bewertungs-, Speicher-, Datenmodell-, Navigations- oder Fachlogik; die bestehende skalierbare Mindestgröße sowie die drei getrennten Workspace-Zonen bleiben erhalten.

## Premium UI Sprint 4 - Visual Signature und Release Polish

### Changed

- Product Shell mit einem sehr ruhigen blau-grauen Arbeitsflaechenverlauf und einer tonal abgestuften tiefblauen Sidebar als finale visuelle Signatur verfeinert.
- Glasakzente auf Navigation, Suche, Filter, Menues, Tooltips und kleine Overlays begrenzt; Inhaltskarten, Tabellen, Formulare und Dokumentflaechen bewusst opak gehalten.
- Kartenhierarchie ueber feine Tiefenkanten statt starker Floating-Schatten praezisiert und die vorhandene interaktive Card-Elevation kuerzer, naeher an der Flaeche und ruhiger abgestimmt.
- Dashboard-, Profil-, Bericht- und LEG-Fokusbereiche ohne Groessen-, Workflow- oder Farbsemantikaenderung klarer von sekundaeren Flaechen getrennt.
- Tabellenheader, Hover und Auswahl sowie Kontextmenues, Tooltips und Scrollbars auf denselben ruhigen blau-grauen Kontrastvertrag ausgerichtet.

### Not Changed

- Keine neue Funktion, Fachlogik, Datenmodell-, SQLite-, Persistenz-, Repository-, Service-, Adapter-, ViewModel-, Workflow-, Navigations- oder Screen-Aenderung; keine neuen Animationstypen und kein QPainter.

## UI Fix - Kursfarben als Kontextbadges

### Added

- Wiederverwendbares `CourseBadge` mit sichtbarem Kursnamen, bestehender Stammdatenfarbe, neutralem Fallback und eindeutigem Accessible Name ergänzt.

### Changed

- Kurszugehörigkeit in Schülerliste, Schülerprofil und bei passenden Kindern im Dashboard als kleinen, kontrastreichen Pastellchip dargestellt.
- Vorhandene Kursfarben aus der bestehenden Adapter-/ViewModel-Projektion wiederverwendet; vollständige Karten und Tabellenzeilen bleiben ungefärbt.

### Not Changed

- Keine Änderung an Datenmodell, SQLite, Persistenz, Kurslogik, Kompetenzstatus, Entwicklungsdarstellung, Dokumentationsfarben, Navigation oder Workflows.

## Premium UI Sprint 3 - Informationsdichte und Accessibility

### Added

- Appweite Tastaturkürzel für lokale Suche (`Ctrl/Cmd+F`) und Speichern (`Ctrl/Cmd+S`) sowie Enter-/Doppelklick-Aktivierung in den bestehenden produktiven Tabellen ergänzt.
- Explizite Accessible Names für Hauptnavigation, kleine Eingabedialoge, Stundenplansteuerung, Statuswechsel und die Dokumentationsmatrix ergänzt.
- Gezielte Offscreen-Regressionstests für Empty States, Tabellenaktivierung, Tastaturkürzel, Badge-Accessibility und farbunabhängige Matrixwerte ergänzt.

### Changed

- Schüler- und Stammdatentabellen auf kompakte Produktlisten mit ruhigen Headern, 44- bis 46-Pixel-Zeilen, zeilenweiser Auswahl, Hover-, Fokus- und Auswahlzuständen, inhaltsgerechten Spalten sowie pixelweisem Scrollen verdichtet.
- Technische Leer-Tabellen durch erklärende Empty States ersetzt; bestehende leere Zustände in Dashboard, Profil, Beobachtung, Bericht, LEG, Einstellungen und Dialogen um Ursache und nächsten sinnvollen Schritt ergänzt.
- Kompetenzbäume und Standardlisten zentral mit klareren Zeilenabständen, Fokus- und Auswahlzuständen versehen; die bestehende Hierarchie `Fach → Kompetenzbereich → Thema → Kompetenz` bleibt unverändert.
- Statusbadges vereinheitlicht, ihren gesprochenen Namen mit sichtbaren Textänderungen synchronisiert und die Dashboard-Dokumentationsmatrix zusätzlich mit sichtbaren Zahlenwerten statt alleiniger Farbintensität versehen.
- Formularfelder in Schüler-, Stammdaten- und Stundenplandialogen explizit für Screenreader benannt; vorhandene Enter-, Escape-, Pfeiltasten- und Tab-Reihenfolgen bleiben erhalten.

### Not Changed

- Keine Änderung an Fachlogik, Datenmodell, SQLite, Migrationen, Repositories, Services, Adaptern, ViewModels, Workflows, Navigation, Datenquellen oder fachlichen Statusregeln; keine neue Funktion, kein neuer Screen und kein QPainter.

## Kompetenz-Entwicklungskarten UX Fix

### Changed

- Lernentwicklungskarten im Schuelerprofil auf Kompetenz, Fach/Thema, textgestuetzte Ausgangslage, aktuellen dokumentierten Stand und genau einen datierten realen Beleg verdichtet.
- Die Status `--`, `-`, `+` und `++` mit ruhigen Pastell-Badges sowie einem neutralen Abwaertspfeil dargestellt, ohne Score-, Leistungs- oder Ampelsemantik.
- Separate Beobachtungsbuttons entfernt und die gesamte Karte inklusive Hover, Fokus und Tastaturbedienung an die bestehende Beobachtungs- beziehungsweise Kompetenznavigation angebunden.
- Historische Referenzen auf ein dezentes Badge reduziert und die Karten fuer 1180 x 760 sowie 1400 x 900 kompakt gehalten.

### Not Changed

- Keine Aenderung an Kompetenzlogik, Statusermittlung, Ereignisauswahl, Datenmodell, IDs, Persistenz, Bewertung oder kanonischer Profilprojektion.

## Kompetenz-Cockpit UX Fix - Direkte Karteninteraktion

### Changed

- Kompetenzbereiche, Themen und Kompetenzzeilen im Schuelerprofil reagieren nun auf die gesamte sichtbare Karte sowie auf Enter und Leertaste; die vorhandenen `Öffnen`-Aktionen bleiben zusaetzlich nutzbar.
- Verschachtelte Cockpit-Karten nehmen ihre Interaktion lokal an, sodass ein Klick auf `Arithmetik` nicht mehr bis zur uebergeordneten Fachkarte durchgereicht wird und zu `Mathematik` zurueckspringt.
- Hover-, Fokus- und Pressed-Zustaende der direkt bedienbaren Cockpit-Karten zentral im Desktop-Theme sichtbar gemacht.

### Not Changed

- Keine Aenderung an Kompetenzlogik, Datenmodell, IDs, Filtern, Klassenstufen, Statusprojektion, Auswahlregeln, historischen Schutzregeln oder Persistenz.

## Sprint 10B - LEG-PDF aus unveraenderlicher Revision

### Added

- Eigenes unveraenderliches LEG-PDF-Artefakt `LCA` fuer genau eine aktuelle `completed`-`LCV` mit Dateigroesse, Snapshot- und PDF-SHA-256 sowie Erzeugungszeitpunkt ergaenzt.
- Snapshotbasierte LEG-PDF-Projektion mit Schuelerkontext, Gespraechsdatum, verantwortlicher Lehrkraft, gemeinsamen Ergebnissen sowie ausgewaehlten Kompetenz- und Beobachtungsbelegen eingefuehrt.
- Idempotente Erzeugung, verwaltete studentenzentrierte Dateiablage und Integritaetspruefung bestehender Artefakte umgesetzt.

### Changed

- Schreibgeschuetzte aktuelle LEG-Revision um die Aktion `Finales PDF erstellen` und einen ruhigen Artefaktstatus erweitert.
- Bestehenden reinen PDF-Renderer als technische Infrastruktur wiederverwendet, ohne Berichtsentitaeten, Berichtstatus oder Berichtsinhalte in die LEG-Domain zu uebernehmen.

### Not Changed

- LCD, LCF und LCV bleiben in Bedeutung und Lebenszyklus unveraendert; Draft, Live-Projektionen und aktuelle Kompetenz-/Beobachtungsdaten sind keine PDF-Quellen.
- Keine Archivierung, Verschluesselung, Renderer-Versionierung, Mehrfachartefakte, Rollenlogik oder Berichtsdomain eingefuehrt.

## Premium UI Sprint 2 - Dialog Experience and Workspace Polish

### Added

- Wiederverwendbaren `DialogHeader` mit Kontexticon, Titel, sichtbarem Arbeitskontext, optionaler Beschreibung und stabiler Aktionszone fuer produktive PySide-Dialoge eingefuehrt.
- Sechs zentrale Outline-SVGs fuer Schueler-, Stammdaten-, Stundenplan-, Beobachtungs-, Berichts- und LEG-Dialoge ergaenzt.
- Verlustwarnung fuer ungespeicherte Aenderungen in der Berichtswerkstatt mit sicherer Standardaktion `Weiter bearbeiten` ergaenzt.

### Changed

- Kleine Schueler-, Stammdaten- und Stundenplandialoge in klare Groessenrollen, Card-basierte Feldgruppen, Labels oberhalb der Felder, Inline-Validierung und eine einheitliche Aktionshierarchie ueberfuehrt.
- Beobachtungsdialog als Drei-Zonen-Workspace visuell gewichtet und Kopf, Kontext sowie feste Speicherzone vereinheitlicht; Kompetenz- und Speicherlogik bleiben unveraendert.
- Berichtswerkstatt, Finalisierungsbestaetigung, finale Revision, LEG-Workspace, Dirty-Close und Draft-Auswahl auf dieselbe Dialogkopfsprache ausgerichtet; Draft, Vorschau und Revision bleiben klar getrennte Zustaende.
- Native Bestaetigungs- und Fehlerdialoge zentral typografisch beruhigt sowie Fokus, Enter-/Escape-Defaults und die Reihenfolge sekundaerer und primaerer Aktionen konsolidiert.

### Not Changed

- Keine Aenderung an Fachlogik, Datenmodell, SQLite, Migrationen, Repositories, Services, Adaptern, ViewModels, Navigation, Persistenz, fachlichen Workflows oder bestehenden Dialogtypen; keine neue Funktion, kein QPainter und keine zusaetzliche Motion.

## Sprint 10A - LEG-Abschluss und Revision

### Added

- Eigenes stabiles LEG-Aggregat `LCF` und unveraenderliche `LCV`-Revisionen mit kanonischem Abschluss-Snapshot und SHA-256 ergaenzt.
- Expliziten Abschlussbefehl mit typisierter Validierung, atomarer Revisionierung und idempotenter Behandlung identischer Snapshots eingefuehrt.
- Snapshotbasierte schreibgeschuetzte Revisionshistorie mit Integritaetspruefung vor der Anzeige ergaenzt.

### Changed

- LEG-Workspace um einen getrennten Abschlussstatus, die Aktion `Gespräch abschließen` und den Zugriff auf historische Revisionen erweitert.
- Fehlende oder ungueltige ausgewaehlte Referenzen blockieren den Abschluss; vollstaendig aufloesbare historische Kompetenzreferenzen werden gekennzeichnet eingefroren.

### Not Changed

- Der `LCD` bleibt bearbeitbar und live-referenzierend; keine Berichtsdomainmodelle, LEG-PDF-, Archivierungs- oder Renderer-Versionierungsfunktion wurden eingefuehrt.

## Premium UI Sprint 1 - Desktop Finish Foundations

### Added

- Konsistentes Outline-SVG fuer ComboBox- und Datumsfeld-Disclosure ergaenzt; die technische Qt-Standardmarkierung wird nicht mehr sichtbar.
- Dezente, systemweite Desktop-Scrollbars sowie ruhige Menu-, Tooltip-, Tab- und Divider-Zustaende in das zentrale Theme aufgenommen.

### Changed

- Product Shell mit ausgewogenerer Sidebar-Breite, leisem Active State, eindeutigem Selection-Indicator, ruhigeren Gruppierungen und grosszuegigerem Inhaltsabstand verfeinert.
- Kartenvertrag gegen Object-Name-Ueberschreibungen abgesichert und Surface, Rahmen, Radien, Tabellen, Typografie, Buttonrollen, Eingabefelder, Fokus-, Hover-, Pressed- und Disabled-Zustaende zentral harmonisiert.
- Stundenplanaktionen semantisch als sekundaer beziehungsweise destruktiv ausgezeichnet, Dialogaktionen vereinheitlicht und die vorhandene Card-Motion zu einer weicheren, layoutneutralen Elevation verfeinert.

### Not Changed

- Keine Fachlogik, Daten, SQLite-, Schema-, Repository-, Service-, Adapter-, ViewModel-, Navigations-, Workflow-, Dialogablauf- oder Produktentscheidungsänderung; kein QPainter und keine neuen Funktionen.

## Sprint 9A - Finaler PDF-Druck aus Berichtrevisionen

### Added

- Finalen PDF-Druck ausschliesslich aus der aktuellen unveraenderlichen `finalized`-Berichtrevision ergaenzt; Draft, Live-Projektionen und supersedierte Revisionen sind keine Eingangsquellen.
- Berichtsspezifische unveraenderliche PDF-Artefaktreferenz mit stabiler `RPA-######`-ID, `RPV`-Bezug, relativem verwaltetem Dateipfad, MIME-Type, Dateigroesse, Snapshot-Hash, PDF-SHA-256 und Erzeugungszeitpunkt eingefuehrt.
- Verwaltete Ablage unter `data/documents/<student_id>/reports/<RPT>/<RPV>/` ohne Klarnamen im Dateinamen sowie ruhige PDF-Aktion in der finalen Revisionsansicht ergaenzt.

### Changed

- Snapshotbasierte Revisionsprojektion um sichtbare Revisions-ID erweitert und den vorhandenen reinen ReportLab-Renderer fuer byte-stabile Wiederholungen deterministisch konfiguriert.
- Fehlende Referenzen, ungueltige Snapshotstruktur, abweichender Snapshot-Hash, unzulaessiger Revisionsstatus, Renderfehler sowie fehlende oder beschaedigte bestehende Artefaktdateien werden vor beziehungsweise waehrend der Erzeugung kontrolliert abgefangen.

### Not Changed

- Keine Renderer-Versionierung, komplexe Archivverwaltung, LEG-PDF, Benutzer-/Rollendomain, neue Berichtsinhalte, zweite Kompetenz- oder Berichtsgenerierung und kein Commit.

## Schülerprofil – Variante A produktiv

### Added

- Reine, stichtagsfähige Profil-Dashboard-Projektion auf Basis der kanonischen Kompetenzstatus- und Dokumentationsstatusprojektionen ergänzt.
- Orientierungskarte für höchstens drei reale Kompetenzstatuswechsel mit Beleg, Zeitraum, curricularer Gleichstandssortierung und historischem Snapshot-Bestandsschutz produktiv angebunden.

### Changed

- Produktiven Schülerprofilkopf und Überblick auf die freigegebene Variante-A-Designsprache mit Dokumentationsring, Kompetenzkarte und neutraler Karte `Noch nicht dokumentiert` ausgerichtet.

### Not Changed

- Keine Änderung an SQLite-Schema, Kompetenzmodell, Beobachtungsdialog, Bericht, Lernentwicklungsgespräch, Dashboard oder globaler Navigation.

## UX-Prototyp – Schülerprofil-Dashboard

### Added

- Vollständige Ist-, Rollen-, Architektur- und Accessibility-Analyse des produktiven Schülerprofils unter `prototypes/student_profile_ux/` dokumentiert.
- Zwei vollständig isolierte PySide6-Layoutvarianten mit neun statischen Profilzuständen, lokaler Navigation, Kompetenz-, Beobachtungs-, Dokument- und Verlaufssichten ergänzt.
- Bevorzugte Dashboardvariante mit bis zu drei regelbasiert erkennbaren Kompetenzentwicklungen, neutralem Dokumentationsüberblick, noch nicht dokumentierten Lernbereichen, neuesten Beobachtungen sowie Bericht-/Revisions-/LEG-Kurzstatus ausgearbeitet.
- Verbindliche Screenshots beider Varianten bei 1400 x 900 und 1180 x 760 ergänzt.
- Sechs zusätzliche Referenzscreenshots für Mathematik, Deutsch, Empty State sowie die beiden Kompetenzkartenstudien ergänzt, ohne bestehende Bilder zu überschreiben.
- Eigenständige UX Discovery mit sechs grundverschiedenen Denkmodellen für Kompetenzentwicklung, nachvollziehbarer Bewertung und eindeutiger Entscheidung für belegbasierte `Beobachtungskapitel` ergänzt.
- Isolierten PySide6-Mockup der Beobachtungskapitel bei 1400 x 900 und 1180 x 760 ergänzt: aktueller dokumentierter Stand, reale Ereigniskarten und explizite Statuswechsel statt Kurve, Achse oder Interpolation.

### Changed

- Gemeinsames Kompetenz- oder Themendiagramm der Variante A durch eine Orientierungskarte ersetzt: höchstens drei Kompetenzen mit mindestens zwei realen Ereignissen und mindestens einem Statuswechsel, sortiert nach jüngster tatsächlicher Änderung und curricularer Reihenfolge.
- Jede ausgewählte Kompetenz als eigene kompakte, belegverknüpfte Zeile mit Kurzbezeichnung, `Fach · Thema`, früherem und neuem Status sowie Zeitraum dargestellt; die zeitliche Verbindung dient ausschließlich der Orientierung zwischen dokumentierten Ereignissen und bildet keinen kontinuierlichen Verlauf ab.
- Statische Demokompetenzen und -ereignisse ergänzt, damit Verbesserung, zwischenzeitliche Verschlechterung, unveränderte Mehrfachereignisse, Einpunkt-, Leer-, Mehr-als-drei-, Fachwechsel- und Historienzustände prüfbar bleiben, ohne fehlende Dokumentation als Status oder künstliche Linie darzustellen.
- Profilkopf mit Avatar, ruhigen Stammgruppen-/Kurschips und neutralem Dokumentationsring gestärkt; Kompetenzkarte, Dokumentzeilen und Hierarchie der neuesten Beobachtungen kompakter ausgearbeitet.
- Fach- und Themenchips als Steuerung, gemeinsame Statusachse, mehrere Kompetenzlinien, Legende und Treppenlinien aus der Übersicht der Variante A entfernt; keine Noten-, Score-, Prozent-, Mittelwert-, Ranking-, Lerngeschwindigkeits- oder automatische Trendlogik ergänzt.
- Den bestehenden chronologischen lokalen Bereich in Variante A als `Entwicklung` bezeichnet; Variante B behält unverändert `Verlauf`.

### Not Changed

- Keine produktive Schülerprofil-, Navigations-, Fachlogik-, Kompetenzstatus-, Bericht-, LEG-, Persistenz-, Schema-, Migrations- oder Teständerung.
- Keine SQLite-, Repository-, Adapter- oder produktive ViewModel-Anbindung des Prototyps.

## UI Sprint 6B - Phasenorientierter LEG-Workspace

### Added

- Kompakte, tastaturfähige LEG-Phasenleiste mit den sechs bestehenden Gesprächsphasen und ausschließlich den lokalen Zuständen `Aktuell`, `Inhalt vorhanden` und `Noch leer` ergänzt.
- Zentralen Dirty-State für Texte, Datumsfelder sowie Kompetenz-, Beobachtungs- und Diagrammauswahl mit sicherem Drei-Wege-Schließen, Inline-Speicherfehler und Toast-Erfolg eingeführt.
- Ruhige Mehrfach-Draft-Auswahl mit Gesprächsdatum, Lehrkraft und gespeichertem Stand ergänzt; technische Draft-IDs dominieren die Auswahl nicht.

### Changed

- Den bisherigen langen Zwei-Spalten-Dialog in einen stabilen Kontextkopf, eine lokale Phasenleiste, genau eine aktive Schreib-/Auswahlphase und eine persistente Aktionsleiste umgebaut.
- Vorbereitung der Lehrkraft, gemeinsam bearbeitete Gesprächsinhalte und im Draft festgehaltene Vereinbarungen durch Rollenlabels und Kartenhierarchie getrennt; `agreed_goals_text` erscheint ohne Persistenzänderung in Phase 4.
- Kompetenz-, Beobachtungs- und Diagrammauswahl in Phase 5 konzentriert; die übrigen Phasen zeigen eine read-only Belegzusammenfassung mit direkter Navigation zu Phase 5.
- Optionalen Überprüfungstermin für neue Drafts leer statt mit dem aktuellen Datum vorbelegt und den Profilmenütext auf `Lernentwicklungsgespräch öffnen` präzisiert.
- Produktive Mindestgröße auf 1080 x 700 gesenkt; 1400 x 900, 1280 x 800 und 1180 x 760 bleiben ohne horizontalen Gesamtscroll bedienbar.

### Not Changed

- Keine Änderung an `LearningConferenceDraft`, SQLite-Schema, Migrationen, Feldbedeutungen, IDs, Validierung, Repository-, Service-, Adapter- oder Speicherregeln.
- Keine Abschluss-, Finalisierungs-, Revisions-, Snapshot-, PDF-, Druck-, Export-, Autosave- oder Berichtsfunktion ergänzt.

## UI Sprint 6A - LEG UX Audit und Zielbild

### Added

- `docs/LEG_UX_AUDIT_AND_TARGET.md` dokumentiert den bestehenden persistenten LEG-Draft, die sechs produktiven Gespraechsphasen und das verbindliche UX-Zielbild fuer UI-Sprint 6B.

### Not Changed

- Keine produktive UI, Fachlogik, Persistenz, Tests, Abschluss-/Revisionslogik oder LEG-Ausgabe wurde geaendert.

## UI Sprint 5 - Berichtswerkstatt, Finalisierung und Revisionen

### Changed

- Berichtswerkstatt in die vier tastaturfaehigen lokalen Bereiche `Schreiben`, `Kompetenzen & Belege`, `Vorschau` und `Revisionen` gegliedert; Fachtexte und Auswahlworkspace konkurrieren nicht mehr gleichzeitig um Aufmerksamkeit.
- Kompakten Berichtskopf mit Kind, Stammgruppe, Berichtstyp, Zeitraum, verantwortlicher Lehrkraft, Draftstatus und aktuellem Revisionskontext eingefuehrt; technische Draft-, Revisions- und Hashwerte bleiben aus dem Hauptbereich herausgenommen.
- Primaere Draftaktion in einer dauerhaft erreichbaren Aktionsleiste auf `Entwurf speichern` konzentriert; Vorschau, Schliessen und der raeumlich getrennte Finalisierungsbereich verwenden passende zentrale Buttonrollen.
- Draft-Vorschau eindeutig als Vorschau des aktuellen Entwurfs gekennzeichnet und ihre tatsaechliche Quelle als gespeichert beziehungsweise noch ungespeichert ausgewiesen; bestehender Draft-PDF-Weg bleibt als `Entwurfs-PDF exportieren` klar abgegrenzt.
- Finalisierungsbestaetigung, neuestes-zuerst sortierte Revisionshistorie und snapshotbasierte finale Leseansicht zu ruhigen Pruef- und Dokumentflaechen modernisiert; finale Revisionen zeigen ausschliesslich `Zurueck` und keine irrefuehrende finale PDF-Aktion.
- Semantische UI-Tests fuer Berichtskopf, alle Statuszustaende, lokale Navigation, getrennte Schreib-/Auswahlbereiche, Draft-Kennzeichnung, Finalisierung, Accessibility, Zielgroessen und unveraenderliche Revisionsansicht erweitert.

### Not Changed

- Keine Fach-, Validierungs-, Finalisierungs-, Snapshot-, Hash-, Revisions-, Schema-, Repository-, Service-, Adapter-, PDF-Artefakt-, Berichtstyp-, Zeitraum- oder historische Referenzregel geaendert.

## Sprint 5B.3 - Bericht finalisieren und Revisionen anzeigen

### Added

- Berichtswerkstatt um ruhigen Finalisierungsstatus, bewusste Erst- und Folgerevision, handlungsorientierte Inline-Validierung sowie ein neuestes-zuerst sortiertes schreibgeschuetztes Revisionsprotokoll ergaenzt.
- Zentrale Read-API fuer Berichtaggregat, aktuelle Revision, Revisionshistorie, einzelne `RPV`-Revision, Snapshot-Hashpruefung und deterministische Draft-Aenderungserkennung umgesetzt.
- Vollstaendig schreibgeschuetzte finale Revisionsansicht und renderer-neutrale `LearningReportRevisionViewModel`-Projektion eingefuehrt; beide lesen ausschliesslich gespeichertes `snapshot_json`, Revisionsmetadaten und SHA-256.
- Ernsthafte, nicht destruktiv gestaltete Finalisierungsbestaetigung mit Kind, Berichtstyp, Zeitraum, Fach-, Kompetenz- und Beobachtungsumfang, neuer Revisionsnummer und verpflichtendem Lehrkraft-Anzeigenamen ergaenzt.

### Changed

- Der produktive Finalisierungsweg speichert ungespeicherte Draftaenderungen zuerst, validiert anschliessend zentral und aktualisiert Status und Historie ohne automatische PDF-Erzeugung.
- `ReportOutputModel` erhaelt fuer finale Revisionen eine getrennte snapshotbasierte Adapterprojektion; die bestehende Draft-Vorschau und Draft-PDF-Anbindung bleiben live und unveraendert getrennt.

### Not Changed

- Keine Schema- oder Migrationserweiterung, kein finales PDF-Artefaktmodell, keine Artefaktverwaltung, Archivierung, Renderer-/Templateversionierung, LEG-Finalisierung, Benutzer-/Rollendomain oder globale Berichtsnavigation.

## Sprint 5B.2 - Unveraenderliche Berichtrevisionen im Backend

### Added

- Verbindliche Product-Owner-Entscheidungen fuer verantwortliche Selbstfinalisierung per Anzeigename, Mindestanforderungen, getrennten spaeteren LEG-Abschluss, Korrekturen als Folgerevisionen und den fachlichen Snapshot als historische Source of Truth dokumentiert.
- Stabile `RPT`-Berichtaggregate und unveraenderliche `RPV`-Revisionen mit berichtsspezifischem Snapshotvertrag, kanonischem JSON und SHA-256 als additiven Backendpfad umgesetzt.
- Additive, idempotente SQLite-Migration, transaktionale Erst- und Folgerevision, Datenbank-Guards gegen Revisionsaenderung oder -loeschung sowie Finalisierungsvalidator, Snapshot-Builder, Repository, Domain-Service und Application Command ergaenzt.
- Abschlussreview: Die mit Revision 1 festgelegte `RPT`-Identitaet aus Quell-Draft, Kind, Berichtstyp und Zeitraum wird gegen spaetere Draftabweichungen geschuetzt. `learning_reports` kann nach Erstellung weder aktualisiert noch geloescht werden; ein anderer Zeitraum oder Berichtstyp erfordert einen neuen Draft.

### Changed

- Der freigegebene Lifecycle unterscheidet nun explizit den weiter bearbeitbaren `RPD`, das pro Draft stabile `RPT` und die nummerierte unveraenderliche `RPV`; Sprint 5A bleibt ein nicht bindender Vorschlag.
- Fokussierte Finalisierungs-, Migrations-, Hash-, Historien- und Rollbacktests sowie bestehende Bericht-, PDF- und LEG-Regressionen sichern den neuen Backendpfad ab.

### Not Changed

- Keine UI-Aktion oder Aenderung der Berichtswerkstatt, kein finales PDF, keine Artefakt- oder Dateiverwaltung, keine Renderer-Versionierung, Archivierung, LEG-Finalisierung, gemeinsame Bericht-/LEG-Domain, Benutzer-/Rollendomain oder automatische Draftmigration.

## Sprint 5B.1 - Historische Berichtreferenzen bestandssicher

### Changed

- Beim Oeffnen eines gespeicherten Berichtsdrafts werden dessen Kompetenz-IDs als Lesekontext an die kanonische Kompetenzprojektion uebergeben; spaeter deaktivierte oder historische Auswahlen bleiben gekennzeichnet erhalten und koennen nur abgewaehlt, nicht neu ausgewaehlt werden.
- Das Bericht-Repository unterscheidet bei Kompetenzen und Beobachtungen neue von bereits gespeicherten Referenzen. Neue inaktive, fremde oder fachfremde Referenzen werden abgewiesen; gespeicherte spaetere Ausfaelle bleiben bis zur ausdruecklichen Abwahl erhalten.
- Nicht mehr verfuegbare gespeicherte Beobachtungs-IDs werden ohne rekonstruierte Inhalte in Berichtswerkstatt, Qt-Vorschau und neutralem `ReportOutputModel` ausgewiesen; der bestehende PDF-Renderer verarbeitet weiterhin nur dieses Ausgabemodell.
- Fokussierte Persistenz-, UI-, Vorschau- und Output-Regressionen fuer Bestandserhalt, Neuauswahlverbot, Abwahl und Referenzgrenzen ergaenzt; die vorhandene PDF-Regression bleibt gruen.

### Not Changed

- Keine neue Tabelle oder Migration; `RPD`, `CMP` und `OBS`, bestehende Berichtstabellen, Berichtsdraft-Aggregat, LEG-Aggregat und PDF-Renderer bleiben erhalten.
- Keine Finalisierung, Revision, Snapshots, Hashes, Artefaktverwaltung, Renderer-Versionierung, LEG-Aenderung, UI-Neugestaltung oder Universal-Workflow-Engine und kein Commit.

## Sprint 5A - Product Discovery und Architecture Gate fuer Bericht und LEG

### Added

- Nicht bindenden Produkt- und Architekturvorschlag fuer Bericht, LEG, Live-Daten, Snapshots, Abschluss, Versionierung, Korrekturen, Vorschau, PDF-Artefakte, Migration und Folge-Sprints ergaenzt.

### Changed

- Bestehende Draft-, Vorschau-, Export-, PDF- und LEG-Wege belastbar als implementiert, nur dokumentiert, im Pilottest erwartet oder offen/widerspruechlich eingeordnet.

### Not Changed

- Keine Produktcode-, UI-, SQLite-Schema-, Migrations-, Test-, Seed-, ADR- oder bestehende Governance-Entscheidung geaendert.

## UI Sprint 4 - Schuelerprofil, Kompetenz-Cockpit und Beobachtungs-Workspace

### Added

- Gemeinsame Workspace-Sprache fuer Profil, Kompetenz-Cockpit und Beobachtungsdialog mit dauerhaft sichtbarem Kindkontext, lokaler Segmentnavigation, zentralen Cards, Section Headers, Suche, Statuskennzeichnungen und kontextueller Hilfe ergaenzt.
- Lokale Klassenstufenfilter `Passende Kompetenzen`, `Klassenstufe 4` und `Alle Kompetenzen` auf Basis der bestehenden `learning_stage`-Metadaten in Profil und Beobachtungsdialog eingefuehrt.
- Inline-Validierung, ruhige Dateizeilen, Accessibility-Vertraege sowie responsive Regressionen fuer 1400 x 900, 1280 x 800 und 1180 x 760 ergaenzt.

### Changed

- Profilkopf und Aktionshierarchie auf genau eine dominante Aktion `Neue Beobachtung`, sekundaeres Dateiangebot und ein Menue fuer seltenere bestehende Aktionen konzentriert.
- Beobachtungslisten, Kompetenzhierarchie und Drei-Zonen-Dialog auf das zentrale Surface-, Button-, Search-, Badge- und Motion-System umgestellt; Disclosure bleibt daten- und zustandssicher und nutzt nur kurze Opacity-Rueckmeldung.
- Beobachtungs-Kompetenzprojektion um das bereits vorhandene Katalogfeld `learning_stage` erweitert; weder Fachlogik noch gespeicherte Werte wurden veraendert.

### Not Changed

- Keine Aenderung an SQLite-Schema, Datenmodell, Bewertungslogik, Kompetenzzuordnung, historischen Regeln, Repositories, Schreibprozessen, Lehrplaninhalten, Bericht/LEG, Exporten oder Legacy Excel/VBA.
- Kein QPainter-Einsatz; Standardwidgets und zentrales QSS decken Hierarchie, Fokus, Auswahl und Dateidarstellung High-DPI-sicher ab.

## UI Sprint 3 - Motion System und Microinteractions

### Added

- Zentrales, Qt-basiertes Motion-System mit einheitlichen Dauer-, Easing-, Lifecycle- und Reduced-Motion-Regeln ergaenzt.
- Kurze funktionale Microinteractions fuer interaktive Karten, Segmentwechsel, Filterchips, Inline-Hinweise und Toasts eingefuehrt.

### Changed

- Toasts pausieren ihre Verweildauer bei Hover, ersetzen laufende Meldungen ohne Animationsstapel und blenden kontrolliert ein und aus.
- Interaktive Karten erhalten dezente Hover-Tiefe; Auswahl, Fokus, Filterausfuehrung und fachliche Aktionen bleiben unmittelbar.

### Not Changed

- Keine Aenderung an Datenmodell, SQLite-Schema, Fachlogik, Repositories, Adaptern, ViewModels, Tabellen, Leerzustaenden, Navigation oder Dialogarchitektur.

## UI Sprint 2 - Premium Components und Workspace Modernization

### Added

- Semantische Basiskomponenten `AppCard`, `SectionHeader`, `FilterBar`, `FilterChip` und `IconButton` fuer wiederverwendbare Surface-, Kontext- und Aktionsmuster ergaenzt.

### Changed

- Heute, Schueler-Workspace, Schuelerliste sowie Stammdaten mit klarerer Surface-Hierarchie, ruhigeren Tabellen, konsistenten Abschnittskoepfen, sichtbaren Filterzustaenden und responsiven Abstaenden modernisiert.
- Bestehende Komponentenvertraege fuer Suche, Status, Leerzustand, Fokus, Auswahl und Accessibility auf Component Library V2 erweitert.

### Not Changed

- Keine Aenderung an Datenmodell, SQLite-Schema, Fachlogik, Repositories, Adaptern, ViewModels, Stundenplanlogik, Profilinhalten, Beobachtungsdialog, Bericht, LEG oder globaler Navigation.

## UI Sprint 1.1 - Schuelerprofil-Zugriff und Kursansicht

### Added

- `Kurse` als viertes lokales Segment im Schueler-Arbeitsraum ergaenzt; die Ansicht nutzt die bestehende Stammdatenreihenfolge und oeffnet die vorhandene `course_id`-Filterprojektion.

### Changed

- Einfacher Klick auf eine Schuelerzeile oeffnet wieder direkt das Profil; Enter und die sekundäre Aktion `Profil öffnen` bleiben erhalten, Doppelklicks werden gegen Mehrfachnavigation abgesichert.
- Eingebettete Zeilenaktionen bleiben eigenstaendig und loesen keine zusaetzliche Profilnavigation aus.

### Not Changed

- Keine Aenderung an Datenmodell, SQLite-Schema, Repositories, Fachlogik, Kursverbundfilter, Profilinhalt, Beobachtungsdialog, Dashboard, Bericht, LEG oder globaler Navigation.

## UI Sprint 1 - Product Shell und Interaction Foundations

### Added

- Lokalen Schueler-Arbeitsraum mit den Segmenten `Stammgruppen`, `Kursverbünde` und `Alle Schüler` sowie bewusstem Drill-down in bestehende ID-basierte Listen eingefuehrt.
- Zentrale UI-Grundkomponenten fuer Page Header, segmentierte Navigation, Suche, Status, Inline-Hinweise, Leerzustaende und nicht blockierende Toast-Meldungen ergaenzt.
- Konsistentes SVG-Shell-Iconset in 16-, 20- und 24-Pixel-Rollen sowie semantische Farb-, Typografie-, Abstands-, Radius-, Elevation- und Motion-Tokens registriert.

### Changed

- Globale Navigation auf `ARBEIT` mit `Heute` und `Schüler` sowie `VERWALTUNG` mit `Stammdaten` und `Einstellungen` reduziert; leere globale Beobachtungs-, Kompetenz- und Berichtsziele entfernt.
- `Dashboard` sichtbar in `Heute` umbenannt und die bisherige globale `Übersicht` in den Schueler-Arbeitsraum integriert.
- Native Systemschrift statt erzwungenem Arial, zentral definierte Buttonrollen und klar sichtbare Hover-, Aktiv-, Fokus-, Pressed- und Disabled-Zustaende verwendet.
- Reine Zeilenauswahl in der Schuelerliste vom Profiloeffnen getrennt; Profil wird per Doppelklick, Enter oder expliziter Aktion geoeffnet.
- Dokumentationsmatrix auf neutrale Blau-Grau-Abstufungen ohne Ampel- oder Leistungssemantik umgestellt und App-Info von ueberholten Prototyp-/Nicht-Persistenz-Hinweisen bereinigt.

### Not Changed

- Keine Aenderung an Datenmodell, SQLite-Schema, Migrationen, Repositories, Adaptern, ViewModels, Stundenplan-, Beobachtungs-, Kompetenzstatus-, Berichts-, LEG- oder PDF-Fachlogik.
- Keine Excel-/VBA-, Prototyp-, Dark-Mode-, QPainter- oder vollstaendige Dialog-/Profil-Neugestaltung.

## Dashboard-UX - Beobachtungsaktionen vereinfachen

### Changed

- Redundante Aktion `+ Beobachtung` aus der hervorgehobenen Stundenkarte entfernt; der globale Header-Einstieg und die kindbezogenen `Beobachten`-Aktionen bleiben erhalten.

### Not Changed

- Keine Aenderung an Stundenplan-, Beobachtungs-, Adapter-, ViewModel- oder Fachlogik.

## Testdaten - Achtmonatiger produktionsnaher Nutzungsstand

### Changed

- SQLite-Testdatenseed auf 24 kuenstliche Kinder in vier Stammgruppen, drei Kursen und drei Kursverbuenden erweitert.
- Vollstaendigen Wochenstundenplan mit 25 aktiven Stunden und Zielen vom Typ Stammgruppe, Kurs und Kursverbund ergaenzt.
- Fachbezogene Beobachtungshistorie von September bis Juli deckt alle aktiven Katalogfaecher ab und enthaelt bewusst unterschiedliche Dokumentationsdichten, aktuelle und heutige Eintraege, eindeutige Schnellbeobachtungen sowie einen Soft Delete.
- Seed-Regressionstest prueft nun zusaetzlich Wochenplan, Zieltypen, alle aktiven Faecher und alle 24 dokumentierten Kinder.

### Not Changed

- Keine Migration, Schema-, Produktivlogik-, Adapter-, ViewModel- oder Widget-Aenderung und kein Commit.

## Sprint 8B.3 - Passende Kinder als transparente Dokumentationshilfe

### Added

- Kanonische Dashboard-Projektion fuer maximal fuenf aktive Kinder des hervorgehobenen Stundenplanziels ergaenzt. Sie priorisiert ausschliesslich anhand fehlender beziehungsweise letzter aktiver Dokumentation im Stundenfach und erhaelt den Auswertungszeitpunkt explizit.
- `Passende Kinder für diese Stunde` zeigt Name, neutralen Dokumentationshinweis und `Beobachten`; die Aktion oeffnet direkt den bestehenden Beobachtungsdialog mit Fach und Unterrichtskontext.
- Fachlich eindeutige Schnellbeobachtungen werden beruecksichtigt; fachlich uneindeutige, soft-geloeschte, fachfremde und fremde Beobachtungen bleiben ausgeschlossen.

### Not Changed

- Keine Migration, Persistenz-, Schema-, Kompetenzstatus-, Rating-, Score-, Stundenplan- oder Beobachtungsschreiblogikaenderung und kein Commit.

## Sprint 8B.2 - Alte Uebersichtsbereiche aus Dashboard entfernt

### Changed

- Allgemeine Stammgruppen-, Kursverbund- und Schnellzugriffskarten vollstaendig aus dem eigenen Dashboard-Screen entfernt.
- Dashboard endet nun nach Hero-Karte, horizontalem Tagesstundenplan, kompakter Dokumentationsmatrix und `Passende Kinder für diese Stunde`.
- Die getrennte `Übersicht` behaelt ihre bisherigen Stammgruppen- und Kursverbundkarten unveraendert.

### Not Changed

- Keine Aenderung an Stundenplanlogik, Projektionen, Adaptern, ViewModels, Persistenz, Beobachtungspfad oder Navigation; kein Commit.

## Sprint 8B.1 - Dashboard UX an freigegebene Referenz angeglichen

### Changed

- Dashboard als eigenen Hauptnavigationspunkt vor der unveraendert erhaltenen `Übersicht` getrennt und die Screen-Komposition an die freigegebene UX-Referenz angeglichen.
- Hero-Karte auf eine breite 60/40-Arbeitsflaeche mit Unterrichtsinformationen links und bewusst freigehaltenem Illustrationsbereich rechts umgestellt.
- Heutigen Stundenplan als horizontale Timeline-Karten statt vertikaler Liste dargestellt; die laufende Stunde bleibt mit `JETZT` deutlich markiert.
- Dokumentationsuebersicht als kompakte Stammgruppe-mal-Fach-Matrix angeordnet und Karten fuer passenden Unterrichtskontext sowie bestehende Schnellzugriffe referenznah untereinander gesetzt.

### Not Changed

- Keine Aenderung an Stundenplan- oder Dashboardlogik, Adaptern, ViewModels, Persistenz, Datenmodell, Beobachtungspfad oder bestehenden Tests; kein Commit.

## Sprint 8B - Stundenplanbasiertes Dashboard

### Added

- Die bisherige Uebersicht als ruhige Dashboard-Startseite mit zentraler Karte `Für diese Stunde`, kanonisch projizierter aktueller beziehungsweise naechster Stunde und vertikaler Tagesliste umgesetzt.
- Direkte Navigation aus Stundenkarten zu Stammgruppe, Kurs oder Kursverbund sowie fluechtige Fach- und Unterrichtskontext-Vorbelegung fuer den bestehenden Beobachtungsdialog nach Kindauswahl ergaenzt.
- Neutrale Mini-Heatmap `Stammgruppe × Fach` aus der kanonischen Dokumentationsstatusprojektion ergaenzt; sie zeigt ausschliesslich die Anzahl Kinder mit vorhandener Dokumentation und keine Ratings, Leistungen oder Entwicklungsurteile.
- Ruhige Zustaende fuer vor der ersten Stunde, Unterrichtspausen, nach Unterrichtsende, Wochenende, fehlenden Stundenplan und ausschliesslich inaktive Eintraege sowie eine hoechstens minuetliche Aktualisierung ergaenzt.

### Changed

- Die Hauptnavigation benennt die Startansicht als `Dashboard`; bestehende Stammgruppen- und Kursverbund-Schnellzugriffe bleiben unterhalb der neuen Arbeitsstartbereiche erhalten.

### Not Changed

- Keine Migration, Schema-, Repository-, Stundenplan-Schreib-, Kompetenzstatus-, Leistungs-, Score-, automatische Entwicklungs-, Excel-/VBA- oder Stammdatenaenderung und kein Commit.

## Sprint 8A.1 - Stundenplan uebersichtlich neu dargestellt

### Changed

- Die Stundenplaneinstellungen von fuenf schmalen Tagesspalten auf Wochentags-Tabs mit einer breiten, chronologischen Stundenliste fuer den ausgewaehlten Tag umgestellt.
- Primaere Hinzufuegen-Aktion, tagebezogene Leerzustaende, kompakte Stundenzeilen und eine ruhige Darstellung deaktivierter Stunden ergaenzt; die vertikale Scrollbarkeit der Einstellungen bleibt erhalten.
- Das Hauptfenster startet maximiert in der verfuegbaren Fenstergroesse, ohne den Vollbildmodus zu verwenden.

### Not Changed

- Keine Aenderung an CRUD, Validierung, Persistenz, Datenmodell, Migration, Zeitprojektion oder Dashboard und kein Commit.

## Sprint 8A - Produktiver Stundenplan

### Added

- Produktiven Wochenstundenplan fuer Montag bis Freitag in den Einstellungen mit kompakter Kartenansicht und Pflege von Fach, Zielart, Ziel, Beginn, Ende, optionalem Raum sowie Aktivstatus ergaenzt.
- Additive idempotente SQLite-Migration, Domain-Validierung, Application Service, Repository, Desktop-Adapter und ViewModels fuer CRUD, Referenzpruefung und Ueberschneidungsschutz eingefuehrt.
- Kanonische, zeitpunktparametrisierte Leseprojektion fuer aktuelle, naechste und heutige Stunden ergaenzt.
- Fokussierte Persistenz-, Validierungs-, Projektions- und Offscreen-UI-Tests ergaenzt.

### Not Changed

- Keine Dashboard-, Ferien-, Vertretungs-, Kalender-, Excel-/VBA- oder Stammdatenfunktion und kein Commit.

## Sprint 7G.3 - Dokumentierte Kompetenzen im LEG

### Changed

- Die LEG-Kompetenzauswahl zeigt nur noch Kompetenzen mit mindestens einer aktiven kindbezogenen Kompetenzbeobachtung im vollstaendig gesetzten LEG-Zeitraum oder mit einer aktuellen Bestaetigung; ohne vollstaendigen Zeitraum gelten alle aktiven Kompetenzbeobachtungen des Kindes.
- Schnellbeobachtungen, soft-geloeschte Beobachtungen, Belege anderer Kinder und reine Katalogeintraege machen keine Kompetenz sichtbar.
- Leere Themen, Kompetenzbereiche und Fachbaeume werden ausgeblendet und durch einen ruhigen fachbezogenen Leerzustand ersetzt.
- Bereits im Draft ausgewaehlte Kompetenzen bleiben ausserhalb des aktuellen Filters sichtbar, ausgewaehlt und gekennzeichnet; historische Draft-Referenzen werden als expliziter Lesekontext weiterhin ueber die kanonische Projektion aufgeloest.
- Zeitraumfelder koennen fuer neue beziehungsweise nur ueber das Gespraechsdatum definierte Drafts ungesetzt bleiben und aktualisieren den lokalen Sichtfilter ohne automatische Abwahl.

### Not Changed

- Keine Aenderung an Draft-Datenmodell, SQLite-Schema, Migration, Beobachtungen, Bestaetigungen, kanonischer Statuslogik, Berichtsfunktion oder uebriger LEG-UX und kein Commit.

## Sprint 7G.2 - Produktive LEG-Oberflaeche

### Added

- Den freigegebenen Zwei-Seiten-Arbeitsbereich aus `prototypes/learning_conference_ux/` als produktiven PySide-Dialog portiert: links die Vorbereitung, rechts die live synchronisierte Gespraechsmappe mit den sechs freigegebenen Phasen.
- Einen eindeutigen Einstieg `Lernentwicklungsgespräch` im Schuelerprofil ergaenzt; ein einzelner Draft wird direkt geladen, mehrere Drafts werden kontrolliert ausgewaehlt und ein neuer Draft bleibt eine explizite Auswahl.
- Fachbereiche, vier uebergreifende Themen, vierstufige Kompetenzhierarchie, gefilterte Beobachtungsbelege, ruhige Mengenwarnung, drei neutrale Diagrammauswahlen sowie vorbereitete und gemeinsam vereinbarte Inhalte vollstaendig an den persistenten 7G.1-Draft gebunden.
- Historische Kompetenzen und nicht mehr verfuegbare Beobachtungsreferenzen bleiben gekennzeichnet sichtbar; Kompetenzstatus bleibt ausschliesslich lesende kanonische Projektion.
- Zentrale Theme-Regeln und fokussierte Offscreen-Tests fuer Einstieg, Rekonstruktion, Speicherung, Referenzerhalt, Warnung und unveraenderliche Kompetenzstaende ergaenzt.

### Not Changed

- Keine Datenmodell-, Schema-, Migrations-, Berichtsdomain-, PDF-, Kompetenzstatus-, Beobachtungs- oder Prototypaenderung und kein Commit.

## Sprint 7G.1 - Persistenter LEG-Arbeitsentwurf

### Added

- Eigenen persistenten Arbeitsentwurf fuer Lernentwicklungsgespraeche mit stabiler `LCD-######`-ID, Schuelerbezug, Zeitraum, Gespraechsdatum, Status `draft`, verantwortlicher Lehrkraft sowie Erstellungs- und Aenderungszeitpunkt eingefuehrt.
- Gespraechseinstieg, Kindrueckblick, Lehrkraftsicht, Staerken, Entwicklungsfelder, Ziele, Unterstuetzung, Vereinbarungen, Zustaendigkeiten und Ueberpruefungszeitpunkt als ausschliesslich manuell verantwortete Draft-Inhalte gespeichert; vorbereitete und gemeinsam vereinbarte Inhalte bleiben getrennt.
- Fachliche Bereiche, uebergreifende Gespraechsthemen, Kompetenzen, Beobachtungsbelege und neutrale Diagrammtypen als normalisierte Auswahl beziehungsweise stabile Referenzen gespeichert.
- Additive SQLite-Migration sowie Domain-, Repository-, Application-, Adapter- und ViewModel-Pfad fuer Anlegen, Laden, Aktualisieren und Wiedereroeffnen umgesetzt und fokussiert getestet.

### Not Changed

- Keine produktive UI-Portierung, finale Gespraechsdokumentation, Versionierung, Archivierung, Freigabe, Signatur, Elternportal, PDF-Erzeugung oder automatische paedagogische Texte; keine Aenderung an Kompetenzstatus, Beobachtungsbewertung, Berichtsdomain, PDF-Engine oder Prototypen und kein Commit.

## Sprint 7F.2 - 1:1 UX-Portierung Lernentwicklungsbericht

### Changed

- Die produktive Berichtswerkstatt auf die verbindliche Arbeitslogik aus `prototypes/learning_report_ux/` umgestellt: oberer Wechsel zwischen `Bericht bearbeiten` und `Berichtsvorschau`, linke Arbeitsbereichsnavigation, eigene Fachseiten und separate mehrseitige Dokumentvorschau.
- Dokumentkontext, pädagogischen Gesamtblick, Facharbeitsbereiche, manuelle Fachtexte, hierarchische Kompetenzauswahl, bewusst gefilterte Beobachtungsbelege, Diagrammauswahl und Abschluss in die Karten- und Informationshierarchie des Prototyps portiert.
- Beim Öffnen aus dem Schülerprofil wird der zuletzt gespeicherte Entwurf geladen; manuelle Texte und Fach-, Kompetenz-, Beobachtungs- sowie Diagrammreferenzen werden über den vorhandenen Adapter-/Service-/Repository-Pfad gespeichert und beim erneuten Öffnen rekonstruiert.
- Das neutrale Ausgabemodell erhält die vier manuellen Fachtexte und ausschließlich bewusst ausgewählte Diagramme; Vorschau und PDF nutzen weiterhin die vorhandene Kompetenz- und Beobachtungsprojektion sowie den unveränderten Renderer.

### Necessary Deviations

- Die im Demo-Prototyp frei änderbaren Kompetenzstände sind produktiv rein lesend, weil Kompetenzstatus und Bestätigungslogik nicht Teil eines Berichtsentwurfs sind; gespeichert werden ausschließlich `competency_id`-Referenzen.
- Der Abschluss fasst die gespeicherten fachbezogenen nächsten Ziele und Unterstützungsbedarfe zusammen. Zusätzliche globale Abschluss- oder interne Notizfelder wurden nicht eingeführt, weil das freigegebene `report_drafts`-Datenmodell unverändert bleibt.
- Die Diagrammauswahl folgt den drei freigegebenen persistenten Diagrammtypen je Fach statt der rein fiktiven Kompetenzbereichs-Demoauswahl des Prototyps.

### Not Changed

- Keine Änderung am `report_drafts`-Datenmodell, `ReportDraftRepository`, an Kompetenzstatus- oder Beobachtungslogik, `ReportOutputModel`, PDF Engine oder `PdfRenderer`; keine automatische Texterstellung, Scores, Trendlinien oder Leistungsbewertung und kein Commit.

## Sprint 7F.1 - Persistenter Lernentwicklungsbericht-Entwurf

### Added

- Einen persistenten, weiter bearbeitbaren Arbeitsentwurf fuer Lernentwicklungsberichte mit stabiler `RPD-######`-ID, Schuelerbezug, Berichtstyp, Zeitraum, Status `draft`, Lehrkraft, Gesamtblick sowie Erstellungs- und Aenderungszeitpunkt eingefuehrt.
- Manuelle Fachtexte fuer Staerken, Lernentwicklung, Unterstuetzungsbedarf und naechste Ziele je bewusst ausgewaehltem Fach gespeichert.
- Ausgewaehlte Faecher, Kompetenzen, Beobachtungsbelege und neutrale Diagrammtypen in normalisierten Relationstabellen gespeichert; Kompetenz- und Beobachtungsinhalte bleiben in ihren bestehenden Sources of Truth.
- Additive SQLite-Migration, Domain-Service, Application Commands/Queries, Repository, Desktop-Adapter und ViewModels fuer Anlegen, Laden, Aktualisieren und Auflisten von Entwuerfen ergaenzt.
- Fokussierte Tests fuer Migration, Anlegen, Laden, Aktualisieren, Texte, Referenzauswahlen sowie unveraenderte Kompetenz- und Beobachtungsprojektionen ergaenzt.

### Not Changed

- Keine finale Berichtsdomain, Freigabe, Versionierung, Archivierung, Signatur, Elternexportverwaltung oder Berechtigungslogik; keine Aenderung an Kompetenzstatus, Beobachtungslogik, `ReportOutputModel`, PDF Engine oder Renderer und kein Commit.

## Sprint 7F.1 - UX Alignment Lernentwicklungsbericht

### Changed

- Die produktive Berichtsvorbereitung vollständig an die freigegebene Sprint-7C-UX angeglichen: ruhige Kopfzeile, durchgängiger linker Vorbereitungsbereich und rechte mehrseitige Dokumentvorschau mit großzügigem Weißraum.
- Dokumentkontext, pädagogischen Gesamtblick, Fachauswahl, hierarchische Kompetenzauswahl, Beobachtungsbelege sowie Ziele und Unterstützung ohne Wizard- oder Schrittnavigation in klar getrennte Karten überführt.
- Die produktive Fachauswahl zeigt weiterhin immer nur ein Fach mit der Hierarchie Fach -> Kompetenzbereich -> Thema -> Kompetenz; Beobachtungsbelege erscheinen erst nach Auswahl passender Kompetenzen beziehungsweise Bereiche.
- Die bisherige technische Vorschau durch eine drucknahe Dokumentansicht mit Deckblatt, Fachseiten, Abschlussseite, Kopf-/Fußbereich und neutralen Entwicklungsdarstellungen ersetzt.

### Not Changed

- Keine Änderung an Architektur, Datenfluss, Kompetenzstatuslogik, `ReportOutputModel`, PDF Engine, Renderer, Persistenz oder Sprint-7C-/7E-Prototypdateien; kein Commit.

## Sprint 7F - Produktiver Lernentwicklungsbericht

### Added

- Den produktiven, vollständig flüchtigen Lernentwicklungsbericht aus dem Schülerprofil heraus ergänzt: ruhige Berichtsvorbereitung mit Dokumentkontext, manuellem Gesamtblick, fachweise gefilterter Kompetenzauswahl, bewusster Beobachtungsauswahl sowie manuellen Zielen und Unterstützungsangaben.
- Eine eigene Berichtsvorbereitungsprojektion ergänzt, die Kompetenzzustände ausschließlich aus der kanonischen Sprint-6-Projektion übernimmt; aktive `current`-Kompetenzen sind auswählbar, historisch referenzierte Kompetenzen bleiben ausschließlich sichtbar.
- Aus der bewussten Auswahl ein neutrales `ReportOutputModel` mit Dokumentationsabdeckung, datierten Kompetenzständen und Zeitachse ausgewählter Beobachtungen erzeugt und dieses über die Shell an die unveränderte Sprint-7E-PDF-Engine übergeben.
- Fokussierte Tests für Profileinstieg, Fachfilter, Kompetenz- und Beobachtungsauswahl, Ausgabemodell und Verarbeitung durch die PDF-Engine ergänzt.

### Not Changed

- Keine Berichtspersistenz, Migration, neue Tabelle, Versionierung, Archivierung, Freigabe, Signaturverwaltung, automatische Text- oder Zielerzeugung, Scores, Durchschnittswerte, Trendlinien oder automatische Entwicklungsbewertung.
- Keine Änderung an Sprint-7D-/7E-Prototypen, PDF-Output-Modellen oder PDF-Renderer; kein Jahres-, Halbjahres- oder LEG-Bericht und kein Commit.

## Sprint 7E - Isolierter Prototyp der PDF-Engine

### Added

- Eine eigenständige ReportLab-Anwendung unter `prototypes/pdf_engine/` ergänzt, die ein vollständiges neutrales `ReportOutputModel` ohne Datenbank- oder Produktimporte als professionelles siebenseitiges A4-PDF rendert.
- Wiederverwendbare Komponenten für Dokumentationsabdeckung, datierte Kompetenzstände und Beobachtungszeitachsen ergänzt; sie erhalten ausschließlich fertige Darstellungsdaten und erzeugen weder Scores, Trendlinien, Ampeln noch automatische Interpretationen.
- Fiktives Demo-Dokument `Lernentwicklungsbericht` für Mara Beispielkind mit Deckblatt, Gesamtblick, sieben konkreten Zeit-Kompetenzen, Entwicklungsdarstellungen, Beobachtungsbelegen, Zielen, Unterstützung und Abschluss vorbereitet.
- Architektur, Datenfluss, Beispielausgabe, spätere Integrationsgrenze und bewusste Grenzen in der lokalen Prototyp-README dokumentiert.

### Not Changed

- Keine produktive App, SQLite-Verbindung, Datenmodell-, Migrations-, Tabellen-, Persistenz-, UI-, Freigabe-, Versionierungs-, Archivierungs- oder Exportverwaltungsänderung; keine Governance-Dokumente, vollständige Testsuite oder Commit.

## Sprint 7D.1 - UX-Verfeinerung des isolierten Lernentwicklungsgespraech-Prototyps

### Changed

- Den vollstaendig isolierten PySide6-In-Memory-Prototyp auf einen natuerlichen sechsteiligen Gespraechsablauf mit ruhiger Gespraechsmappe ausgerichtet.
- Fachliche Bereiche und uebergreifende Gespraechsthemen getrennt, die linke Kompetenz- und Beobachtungsauswahl unmittelbar danach gefiltert sowie die Kompetenzauswahl einklappbar nach Fach, Kompetenzbereich, Thema und konkreter Kompetenz gruppiert.
- Vier manuell editierbare Leitfadenfelder, eine weiche Empfehlung von drei bis fuenf Beobachtungsbelegen und die visuelle Trennung zwischen Lehrkraftvorbereitung und spaeter gemeinsam getroffener Vereinbarung umgesetzt.
- Den allgemeinen Beobachtungsverlauf entfernt und die optionale Diagrammauswahl auf Dokumentationsabdeckung, datierte Kompetenz-Einzelstaende und die Zeitachse ausgewaehlter Belege reduziert.

### Not Changed

- Keine produktive App, SQLite-Abfrage, Repositorys, Adapter, ViewModels, Migration, Persistenz, PDF-Erzeugung, Produktintegration, Architektur- oder Governance-Aenderung, Tests oder Commit.

## Sprint 6H - Schnellbeobachtung im Beobachtungsdialog

### Changed

- Bewusst kompetenzfreie Schnellbeobachtungen mit verpflichtender Notiz im bestehenden PySide-Beobachtungsdialog ergänzt.
- Schnellbeobachtungen ohne Rating-Zeilen über den bestehenden Beobachtungs-, Adapter-, Service- und SQLite-Pfad speicher- und bearbeitbar gemacht.
- Den kompetenzfreien Zustand im Beobachtungsverlauf dezent gekennzeichnet; Kompetenzstatus- und Fortschrittsprojektionen bleiben mangels Rating-Zeilen unverändert.
- Validierungs-, Persistenz-, Bearbeitungs-, Verlaufs- und Regressionsfälle als Tests vorbereitet.

### Not Changed

- Kein neues SQLite-Feld, keine Migration, keine künstliche Kompetenz, keine Berichts-, LEG-, Prototyp-, Soft-Delete- oder Filteränderung und kein Commit.

## Sprint 7C - Isolierter UX-Prototyp fuer Lernentwicklungsbericht

### Changed

- Einen vollstaendig isolierten, nur mit fiktiven In-Memory-Demo-Daten arbeitenden PySide-UX-Prototyp fuer Berichtsbearbeitung und mehrseitige Berichtsvorschau angelegt.
- Facharbeitsbereiche, manuell verantwortete Berichtstexte, bewusste Evidenz- und Grafikauswahl sowie drei neutral beschriftete Diagrammvarianten fuer Dokumentationsstand und Entwicklungsevidenz prototypisch verbunden.
- Start, Abgrenzung, Demo-Daten, Interaktionen, offene Entscheidungen und vollstaendig entfernbare Prototypdateien in einer lokalen Prototyp-README dokumentiert.
- Die Entwicklungsdarstellung auf eine bewusste, standardmaessig leere Auswahl von Kompetenzbereichen umgestellt; jeder gewaehlte Bereich wird getrennt, datiert und ohne Aggregation oder Trendinterpretation dargestellt.
- Diagrammtexte, Datenhinweise und Markerlegende in umbrechende Layoutbereiche verlagert sowie neutrale Null-, Einpunkt- und Zweipunktzustaende ergaenzt.

### Not Changed

- Keine produktive UI, keine SQLite-Abfrage, Repositorys, Adapter, ViewModels, Migration, Tabellen, Speicherung, PDF-Erzeugung, Integration, Governance-Dokumente, vollstaendige Testsuite oder Commit.

## Fix - Beobachtungsdialog

### Changed

- Die primäre Aktion im Beobachtungsdialog heißt einheitlich `Speichern`; dadurch bleibt die Beschriftung im schmalen Aktionsbereich vollständig lesbar.

### Not Changed

- Keine Änderung am Beobachtungsspeicherprozess, an Dialoglayout, Persistenz, SQLite, Adaptern oder Repositorys.

## Sprint 7B - Product- und Architekturentscheidung fuer Bericht, LEG und PDF

### Changed

- Schuelerprofil als Live-Arbeitsansicht und den spaeteren Lernentwicklungsbericht als eigene, versionierbare fachliche Entitaet mit eingefrorenem Ausgabestand abgegrenzt.
- LEG fachlich vom Bericht getrennt; fluechtige Vorbereitung und spaeter moegliche speicherbare Ziele, Vereinbarungen und Gespraechsergebnisse unterschieden.
- PDF als rein lesendes Ausgabeformat fuer eingefrorene Ausgabemodelle und Diagramme als Darstellung von Dokumentationsabdeckung und Entwicklungsevidenz festgelegt.
- Zielarchitektur, neun zentrale Product-Owner-Entscheidungen, Risiken und die Sprintfolge 7C bis 7F in ADR-050 dokumentiert.

### Validated

- Dokumentations-Diffs auf Whitespace-Fehler und Scope geprueft.

### Not Changed

- Keine UI, keine SQLite- oder Datenmodellaenderung, keine Migration, keine neuen Tabellen oder technischen Namen, keine Codeaenderung, keine Tests und kein Commit.

## Sprint 4C2 - Mathematikkompetenzen fachlich verfeinert

### Changed

- Dreizehn fachlich zu breite Mathematik-Kompetenzen bestandsgeschuetzt auf `legacy` und standardmaessig inaktiv gesetzt; Texte, Hierarchien und IDs bleiben fuer historische Beobachtungen und Bestaetigungen unveraendert referenzierbar.
- Vierzig neue, getrennt bewertbare Mathematik-Kompetenzen mit den global fortlaufenden IDs `CMP-000647` bis `CMP-000686` ergänzt. Der aktive Mathematikbestand umfasst damit 81 `current`-Kompetenzen.
- Die bisherige Sammelkompetenz zu Uhrzeiten durch sieben freigegebene Lernziele fuer volle, halbe, Viertel- und minutengenaue Uhrzeiten sowie Einstellen, Notieren und Uebertragen ersetzt. Analoge und digitale Darstellungen bleiben Darstellungsformen innerhalb dieser Kompetenzen.
- Product-Owner-Regel praezisiert: keine mechanische Atomisierung anhand von Verben; getrennt wird nur bei unterschiedlich bewertbaren Lernstaenden, Lernstufen oder Unterstuetzungsentscheidungen.
- Die neuen Mathematikformulierungen gegen ihre dreizehn Legacy-Vorgaenger geprueft und verlorene Anforderungsmerkmale sowie zu abstrakte Einheiten- und Flaechenbezeichnungen inhaltstreu korrigiert, ohne IDs, Aufteilung oder Lernstufen zu veraendern.
- Sichtbare Texte und Kurzlabels der vierzig neuen Mathematikkompetenzen abschliessend auf korrekte deutsche UTF-8-Zeichen umgestellt; die verbindlichen Einheitenformulierungen fuer `CMP-000675` und `CMP-000676` dabei wortgetreu uebernommen.
- Katalog-, Import-, Beobachtungsdialog-, Kompetenzstatus-, Cockpit- und Berichtstests gezielt auf aktive Nachfolger und den historischen Bestandsschutz angepasst.

### Validated

- Katalogvalidator erfolgreich ausgefuehrt.
- Vergleich gegen den Ausgangskatalog erfolgreich geprueft: 40 `NEW_COMPETENCY`, 13 `STATUS_CHANGED` und 26 `METADATA_CHANGED`; keine `TEXT_CHANGED`, `HIERARCHY_CHANGED`, `LEARNING_STAGE_CHANGED` oder `DELETED_COMPETENCY`.
- Vollstaendige Testsuite erfolgreich ausgefuehrt: 300 Tests bestanden.

### Not Changed

- Keine SQLite-Struktur, Migration, UI-, Adapter-, Repository-, Bericht-/LEG-Architektur oder automatische Uebertragung historischer Bewertungen; keine anderen Faecher und kein Commit.

## Sprint 6D - Filter und leere Zustaende im Kompetenz-Cockpit

### Changed

- Das Kompetenz-Cockpit im Schuelerprofil um eine kompakte, lokale Filterleiste fuer aktive Faecher und kanonische Dokumentationszustaende erweitert. Fach- und Zustandsfilter kombinieren sich, veraendern weder Daten noch Statusprojektion und lassen historische Kompetenzzeilen weiterhin im separaten Abschnitt `Historisch dokumentiert`.
- Fortschrittswerte auf Fach- und Kompetenzbereichsebene bleiben beim Filtern auf dem vollstaendigen aktiven Zielbestand. Nicht sichtbare Themen und Bereiche werden nur visuell ausgeblendet; lokale Aufklappzustaende bleiben fuer weiterhin sichtbare Ebenen erhalten und werden beim Zuruecksetzen wiederverwendet.
- Ruhige leere Zustaende fuer Profile ohne aktive Kompetenzen sowie Filter ohne Treffer ergänzt; Fachkarten mit `0 / Gesamt` bleiben bei passenden aktiven Treffern sichtbar.
- Screen-Tests fuer Fach-, Zustands- und Kombinationsfilter, Fortschrittsbestandsschutz, leere Treffer, Bestaetigungen ohne Beobachtung, neuere Beobachtungen, Historientrennung, Aufklappzustand, Datenunveraendertheit und Ruecksetzen ergänzt.

### Not Changed

- Keine Persistenz-, SQLite-, Schema-, Repository-, Domain- oder Statusregeländerung; keine Klassenstufenfilter, Suche, passende Kompetenzen, Berichte, PDF, LEG, Dashboard, Bewertungsfarben oder Commit umgesetzt.

## Sprint 6C - Kompetenz-Cockpit im Schuelerprofil

### Changed

- Den Reiter `Kompetenzen` als ruhiges, vierstufiges Arbeitscockpit Fach -> Kompetenzbereich -> Thema -> Kompetenz neu aufgebaut. Fach- und Bereichskarten zeigen dokumentiert/gesamt sowie neutrale Fortschrittsbalken; alle Ebenen starten geschlossen und behalten ihren lokalen Aufklappzustand je Schueler.
- Die Cockpit-Hierarchie wird ausschließlich aus der kanonischen Sprint-6B-Statusprojektion abgeleitet. Der Screen berechnet keinen Kompetenzstatus und greift weder auf Adapter noch SQLite zu.
- Historisch referenzierte Kompetenzen in den separaten, standardmäßig geschlossenen Abschnitt `Historisch dokumentiert` verschoben. Undokumentierte aktive Kompetenzen erscheinen erst innerhalb eines geöffneten Themas.
- Kompetenzdetails zeigen Dokumentationszustand, bestaetigten Stand, optionalen Beobachtungsvorschlag, Beobachtungsanzahl und letzte Beobachtung. `Beobachtungen anzeigen` wechselt in den vorhandenen Profilreiter.

### Not Changed

- Keine Filter, Suche, Dashboard-, Berichts-, PDF-, LEG-, Bewertungsfarben-, Stundenplan- oder Klassenstufenfunktionen; keine Persistenz-, SQLite-, Schema-, Repository-, Domain- oder Katalogaenderung und kein Commit umgesetzt.

## Sprint 6B - Kanonische Kompetenzstatus-Projektion

### Changed

- Zentrale Status-Leseprojektion je Schueler und Kompetenz im bestehenden Desktop-Adapter ergänzt. Sie trennt Beobachtungsvorschlag, Lehrkraft-Bestaetigung und chronologische aktive Nachweise; historische Referenzen bleiben lesbar, ohne Katalog- oder Statusdaten zu verändern.
- Dokumentationsfortschritt auf eindeutige konkrete Kompetenz-IDs umgestellt und zusätzlich je Fach und Kompetenzbereich projiziert. Nur aktive `current`-Kompetenzen bilden offene Ziele.

### Not Changed

- Keine neue Schülerprofil-Oberfläche, Filter-UI, Persistenz, Schemaänderung, Migration, automatische Statusübertragung, Berichtsumgestaltung, PDF, LEG, Dashboard oder Commit umgesetzt.

## Sprint 5E - Schnellauswahl Zuletzt verwendet

### Changed

- Produktiven Beobachtungsdialog um die fachbezogene Schnellauswahl `Schnellauswahl` direkt unter der Katalogsuche ergänzt. Sie zeigt bis zu vier eindeutige, aktive `current`-Kompetenzen aus den neuesten aktiven Beobachtungen des aktuellen Schuelers und aktualisiert sich nach erfolgreichem Speichern aus SQLite.
- Schnellauswahl-Chips nutzen die bestehende Auswahlinteraktion mit Maus, Tastatur, Hover und Fokus; bereits ausgewaehlte Kompetenzen bleiben mit Haken sichtbar und deaktiviert. Aktive Katalogsuche blendet die Schnellauswahl vollständig aus.

### Not Changed

- Keine Tabelle, Persistenz, gespeicherte Historie, Repository-/Domain- oder SQLite-Schemaänderung, Tags, Klassenstufenfilter, Stundenplan-Vorbelegung, Bewertungsfarben oder Commit umgesetzt.

## Sprint 5D - Suche im Kompetenzkatalog

### Changed

- Produktiven Beobachtungsdialog um eine lokale, nicht persistente Katalogsuche über Kurzlabel, Kompetenztext, Thema und Kompetenzbereich ergänzt; die Suche verwendet ausschließlich die vorhandene Adapter-/ViewModel-Projektion.
- Suchtreffer öffnen passende Fach-, Kompetenzbereich- und Themenzweige nur visuell. Beim Löschen wird der vorherige manuelle beziehungsweise im Bearbeitungsbestand begründete Aufklappzustand wiederhergestellt.
- Historische oder inaktive Kompetenzen bleiben beim Bearbeiten als Bestand erhalten, werden durch die Suche jedoch nicht als neue Treffer angeboten.

### Not Changed

- Keine SQLite-Abfragen aus dem Dialog, Persistenz, Suchhistorie, Datenbank-/Schemaänderung, Repository-/Domain-Logik, Tags, zuletzt verwendeten Kompetenzen, Klassenstufenfilter, Stundenplan-Vorbelegung, neue Attachment-Logik oder Commit umgesetzt.

## Sprint 5C - Freigegebenen Beobachtungsdialog produktiv umgesetzt

### Changed

- Produktiven `NewObservationDialog` auf die freigegebene skalierbare Drei-Zonen-Arbeitsflaeche mit getrennt scrollbarer Auswahl und getrennt scrollbarem Kompetenzkatalog umgestellt.
- Ausgewaehlte Kompetenzen als kompakte Karten mit Fach, Kompetenzbereich, Thema, Kompetenztext, vier direkt anklickbaren Bewertungs-Chips und kompetenzbezogenem Entfernen umgesetzt; neue Auswahlen werden oben eingefuegt.
- Kompetenzkatalog als geschlossene Hierarchie Fach -> Kompetenzbereich -> Thema -> Kompetenz mit vollstaendig klickbaren und tastaturbedienbaren Kompetenzkacheln umgesetzt; Fachwechsel und Einklappen lassen Auswahl und Einzelbewertungen unveraendert.
- Adapterprojektion fuer neue Beobachtungen auf aktive `current`-Kompetenzen begrenzt; bereits gespeicherte `legacy`- oder inaktive Kompetenzen bleiben beim Bearbeiten mit unveraenderten IDs, Texten und Bewertungen sichtbar und werden dezent als historischer Bestand markiert.
- Dialoginternen Fallback-Hierarchieaufbau entfernt; die produktive Darstellung nutzt ausschliesslich die bestehende `StudentDesktopAdapter`-Projektion und weiterhin die vorhandenen Create-/Update-/Repository- und Attachment-Pfade.
- Dialog- und Adaptertests auf Drei-Zonen-Struktur, geschlossene Neu-Erfassung, gezieltes Oeffnen beim Bearbeiten, Kachelinteraktion, Duplikatschutz, Auswahlreihenfolge, Zustandsbestand, historische Kompetenzen und dauerhaft erreichbares Speichern angepasst.

### Not Changed

- Keine Suche, zuletzt verwendeten Kompetenzen, Tags, Klassenstufenfilter, Stundenplan-Vorbelegung, Datenbank-/Schemaaenderung, neue Attachment-Logik, Bewertungsskala, Terminologie, Migration historischer Daten oder Commit umgesetzt.

## Sprint 5B1 - Visueller PySide6-Prototyp des Beobachtungsdialogs

### Added

- Isolierten, nicht persistenten PySide6-UX-Prototyp fuer die neue Beobachtungs-Arbeitsflaeche unter `src/gui/` mit statischen Beispieldaten, Drei-Zonen-Aufteilung, hierarchischem Kompetenzkatalog und Demo-Interaktionen ergaenzt.
- Startbefehl und Abgrenzung des Prototype-Bereichs in `src/gui/README.md` dokumentiert.

### Not Changed

- Keine produktiven Startpfade, Beobachtungsdialoge, Adapter, ViewModels, Domain-, Application-, Repository-, SQLite-, CSV- oder Legacy-Excel-/VBA-Bestaende geaendert; keine Persistenz, keine Suche, keine Tags, keine Klassenstufenfilter und kein Commit umgesetzt.

## Sprint 4 - Gesamtabschluss und Dokumentationsabgleich

### Changed

- Veraltete Projekt-, Roadmap-, Sprint-, Data-Registry- und Data-Lifecycle-Angaben auf den tatsaechlich umgesetzten lehrplanbasierten Sprint-4-Katalogstand abgeglichen.

### Not Changed

- Keine Kompetenzzeile, ID, Fachformulierung oder Religion-Zeile geaendert; keine UI-, SQLite-, Schema- oder Architekturaenderung und kein Commit umgesetzt.

## Sprint 4B-8 - Lehrplankatalog Ethik und Sozialkompetenz uebernehmen

### Added

- 58 neue Ethik-Kompetenzen aus dem freigegebenen Ethik-Mapping, der Katalog-Konsolidierung und den Product-Owner-Entscheidungen mit den global fortlaufenden IDs `CMP-000577` bis `CMP-000620` sowie `CMP-000633` bis `CMP-000646` ergaenzt.
- 12 neue, eigenstaendige Sozialkompetenzen fuer beobachtbare Zusammenarbeit, Dialog, Gemeinschaftsgestaltung und Konfliktbearbeitung mit den IDs `CMP-000621` bis `CMP-000632` ergaenzt.

### Changed

- Die vollstaendig ersetzten Ethik- und Sozialkompetenz-Bestandskompetenzen als `legacy` markiert und aus den Katalog-Default-Zielen genommen; ihre IDs, Texte und Hierarchien bleiben fuer historische Beobachtungen erhalten.
- Den Katalogimport-Test auf die neue Anzahl aktueller und historischer Ethik- und Sozialkompetenzzeilen sowie eine aktuelle Sozialkompetenz ausgerichtet.

### Not Changed

- Keine bestehenden Kompetenztexte oder Hierarchien umgedeutet, keine IDs wiederverwendet, keine Religion- oder anderen Fachzeilen, keine SQLite-, UI-, Beobachtungsdialog-, Bericht- oder Schema-Aenderung und kein Commit umgesetzt.

## Sprint 4B-7 - Lehrplankatalog Heimat- und Sachkunde / EPU uebernehmen

### Added

- 86 neue EPU-Kompetenzen aus dem freigegebenen Lehrplan-Mapping, der Katalog-Konsolidierung und den Product-Owner-Entscheidungen mit neuen global fortlaufenden IDs `CMP-000491` bis `CMP-000576` in `data/curriculum_catalog_v1.csv` ergaenzt.

### Changed

- Die vollstaendig ersetzten EPU-Bestandskompetenzen als `legacy` markiert und aus den Katalog-Default-Zielen genommen; ihre IDs, Texte und Hierarchien bleiben fuer historische Beobachtungen erhalten.
- Bereits gespeicherte EPU-Bestaetigungen und Beobachtungen bleiben in der bestehenden Kompetenz- und Berichtsprojektion sichtbar, auch wenn ihre Katalogkompetenz inzwischen `legacy` oder inaktiv ist.

### Not Changed

- Keine bestehenden EPU-Kompetenztexte oder Hierarchien umgedeutet, keine IDs wiederverwendet, keine anderen Fachzeilen, keine SQLite-, UI-, Beobachtungsdialog-, Bericht- oder Schema-Aenderung und kein Commit umgesetzt.

## Sprint 4B-6 - Lehrplankatalog Sport uebernehmen

### Added

- 42 neue Sport-Kompetenzen aus dem freigegebenen Lehrplan-Mapping und der Katalog-Konsolidierung mit neuen global fortlaufenden IDs `CMP-000449` bis `CMP-000490` in `data/curriculum_catalog_v1.csv` ergaenzt.
- Die optionalen Lernbereiche Ski- und Eislaufen, Inline Skating und Federball als standardmaessig inaktive Aktivierungsgruppen vorbereitet.

### Changed

- Die vollstaendig ersetzten Sport-Bestandskompetenzen als `legacy` markiert und aus den Katalog-Default-Zielen genommen; ihre IDs, Texte und Hierarchien bleiben fuer historische Beobachtungen erhalten.
- Die aktive Fachauswahl verwendet die bestehende kanonische Fachreihenfolge statt der Reihenfolge der ersten aktiven CSV-Zeile je Fach.

### Not Changed

- Keine bestehenden Sport-Kompetenztexte oder Hierarchien umgedeutet, keine IDs wiederverwendet, keine anderen Fachzeilen, keine SQLite-, UI-, Beobachtungsdialog-, Bericht- oder Schema-Aenderung und kein Commit umgesetzt.

## Sprint 4B-5 - Lehrplankatalog Werken und Schulgarten uebernehmen

### Added

- 34 neue Werken-Kompetenzen aus dem freigegebenen Lehrplan-Mapping und der Katalog-Konsolidierung mit neuen global fortlaufenden IDs `CMP-000395` bis `CMP-000428` in `data/curriculum_catalog_v1.csv` ergaenzt.
- 20 neue Schulgarten-Kompetenzen aus dem freigegebenen Lehrplan-Mapping und der Katalog-Konsolidierung mit neuen global fortlaufenden IDs `CMP-000429` bis `CMP-000448` in `data/curriculum_catalog_v1.csv` ergaenzt.

### Changed

- Die vollstaendig ersetzten Bestandskompetenzen der beiden Faecher als `legacy` markiert und aus den Katalog-Default-Zielen genommen; ihre IDs, Texte und Hierarchien bleiben fuer historische Beobachtungen erhalten.

### Not Changed

- Keine bestehenden Kompetenztexte oder Hierarchien umgedeutet, keine IDs wiederverwendet, keine anderen Fachzeilen, keine SQLite-, UI-, Beobachtungsdialog-, Bericht- oder Schema-Aenderung und kein Commit umgesetzt.

## Sprint 4B-3 - Lehrplankatalog Mathematik uebernehmen

### Added

- 54 neue Mathematik-Kompetenzen aus dem freigegebenen Lehrplan-Mapping und der Katalog-Konsolidierung mit neuen global fortlaufenden IDs `CMP-000295` bis `CMP-000348` in `data/curriculum_catalog_v1.csv` ergaenzt.

### Changed

- Die bisherigen Mathematik-Bestandskompetenzen `CMP-000006` bis `CMP-000010` sowie `CMP-000079` bis `CMP-000098` als `legacy` markiert und aus den Katalog-Default-Zielen genommen.

### Not Changed

- Keine bestehenden Mathematik-Kompetenztexte oder Hierarchien umgedeutet, keine IDs wiederverwendet, keine Deutsch- oder anderen Fachzeilen geaendert, keine SQLite-, UI-, Dashboard-, Beobachtungsdialog- oder Berichts-Aenderung und kein Commit umgesetzt.

## Sprint 4B-2 - Lehrplankatalog Deutsch uebernehmen

### Added

- 82 neue Deutsch-Kompetenzen aus dem freigegebenen Lehrplan-Mapping und der Katalog-Konsolidierung mit neuen global fortlaufenden IDs `CMP-000213` bis `CMP-000294` in `data/curriculum_catalog_v1.csv` ergaenzt.

### Changed

- Die alten groben Deutsch-Bestandskompetenzen `CMP-000001` bis `CMP-000005` sowie `CMP-000063` als `legacy` markiert und aus den Katalog-Default-Zielen genommen.
- Adaptertests auf die Trennung zwischen historischen legacy-IDs und aktuellen Deutsch-Katalogzielen umgestellt.

### Not Changed

- Keine bestehenden Deutsch-Kompetenztexte oder Hierarchien umgedeutet, keine IDs wiederverwendet, keine Mathematik- oder anderen Fachzeilen geaendert, keine SQLite-, UI-, Berichts-, Dashboard- oder Beobachtungsdialog-Aenderung und kein Commit umgesetzt.

## Sprint 4A - Kompetenz-Katalogmodell technisch umsetzen

### Added

- CSV-Katalog um `learning_stage`, `catalog_status`, `catalog_default_active` und `activation_group_key` mit sicheren Defaults erweitert, ohne neue Kompetenzen oder neue Kompetenz-IDs einzutragen.
- SQLite `competencies` um dauerhafte Katalogmetadaten inklusive Quellenkontext, produktbezogener Stufe, Katalogstatus, Katalog-Default-Aktivierung und optionalem Aktivierungsbereich erweitert.
- Migration fuer bestehende Datenbanken ergaenzt; alte Kompetenzen erhalten konservative Defaults und historische Beobachtungsbewertungen bleiben unveraendert.
- Tests fuer leere Datenbank, Alt-Schema-Migration, wiederholten Import, neue Katalogfelder, lokale `active`-Werte, historische Ratings, alte CSV-Dateien und Duplikatfreiheit ergaenzt.

### Changed

- Katalog-Upsert aktualisiert fachliche Katalogmetadaten idempotent, schuetzt aber weiterhin `competencies.active` bei bestehenden `competency_id`s.
- Alte CSV-Dateien ohne Sprint-4A-Spalten werden mit Defaults verarbeitet: `learning_stage = cross_stage`, `catalog_status = current`, `activation_group_key = ''` und `catalog_default_active` aus `is_active`.

### Not Changed

- Keine neuen fachlichen Kompetenzen, keine Aenderung bestehender Kompetenz-IDs, keine Beobachtungsdialog-Aenderung, keine Berichts-/Dashboard-Aenderung, keine Lehrplan-Mapping-Aenderung und keine Migration historischer Beobachtungen oder `observation_competency_ratings`.

## Sprint 4A - Kompetenz-Katalogmodell finalisieren

### Added

- Architektur- und Datenmodell-Empfehlung fuer das zukuenftige Kompetenzkatalogmodell dokumentiert.
- ADR-049 als vorgeschlagene Trennung von quellenbezogenem `grade_band` und produktbezogenem `learning_stage` ergaenzt.
- Vorgeschlagene technische Namen fuer das spaetere Katalogmodell in `docs/TECHNICAL_NAMES.md` registriert.

### Not Changed

- Keine CSV-Aenderung, keine SQLite-Aenderung, keine Migration, keine Code-Aenderung, kein Commit umgesetzt.

## Sprint 4 - Lehrplan-Mapping und Stufenzuordnung

### Added

- Fachweise Lehrplan-Mappings fuer den spaeteren Kompetenzkatalog unter `docs/lehrplan/mapping/` abgeschlossen.
- Verbindliche fachliche Stufenzuordnung fuer Kompetenzen eingefuehrt: `Klassenstufe 1-3`, `Klassenstufe 4` und `stufenuebergreifend`.
- Filtergrundlage dokumentiert: spaeter `Passende Kompetenzen` als Standardansicht, zusaetzlich `Alle Kompetenzen anzeigen`; Kompetenzen werden gefiltert, aber nicht gesperrt.

### Not Changed

- Keine CSV-Aenderung, keine SQLite- oder Schemaaenderung, keine UI-Umsetzung, keine technische Feldentscheidung und keine Aenderung bestehender Kompetenz-IDs.

## Sprint 3D - Hierarchische Kompetenzauswahl im Beobachtungsdialog

### Changed

- Beobachtungsdialog zeigt Kompetenzen in der sichtbaren Struktur Fach -> Kompetenzbereich -> Thema -> konkrete Kompetenz.
- Fachwechsel baut die Kompetenzauswahl aus `StudentDesktopAdapter.list_observation_competency_subject_groups(initial_draft)` neu auf.
- Konkrete Kompetenzen werden als Checkboxzeilen dargestellt; pro ausgewaehlter Kompetenz bleibt eine eigene Bewertungszeile erhalten.
- Bearbeiten bestehender Beobachtungen uebernimmt ausgewaehlte Kompetenzen und Bewertungen aus `initial_draft`.
- Alte aktive Kompetenzen bleiben anhand vorhandener Katalogfelder einsortiert und auswaehlbar.
- UX-Fix: Themen im Beobachtungsdialog sind ausklappbar; neue Beobachtungen starten mit eingeklappten Themen, waehrend Themen mit bestehenden Bewertungen beim Bearbeiten automatisch geoeffnet werden.

### Not Changed

- Keine DB-Migration, keine Katalogaenderung, keine Berichtsanpassung, keine Dokumentationsstand-Anpassung, keine aktive-Faecher-Logik, keine neue Bewertungsskala, kein Status `offen` und keine neue Persistenzlogik umgesetzt.

## Sprint 3C - Hierarchische Kompetenzdaten fuer Beobachtungsdialog

### Added

- Hierarchische Observation-ViewModels fuer Fach -> Kompetenzbereich -> Thema -> konkrete Kompetenz ergaenzt.
- `StudentDesktopAdapter.list_observation_competency_subject_groups(initial_draft)` als additive Projektion fuer einen spaeteren Dialog-Umbau ergaenzt.
- Tests fuer Default-Faecher, dokumentationsrelevante Faecher, konkrete Mathematik-Zeit-Kompetenz `CMP-000083`, alte grobe Kompetenz `CMP-000001`, `initial_draft`-Ratinguebernahme und Bestandsfach-Erhalt ergaenzt.

### Not Changed

- Keine DB-Migration, keine Katalogaenderung, keine Beobachtungsdaten-Migration, keine Berichtsanpassung, keine aktive-Faecher-Logik und keine Dialog-UI-Hierarchie umgesetzt.

## Sprint 3B - Konkreter Kompetenzkatalog und idempotenter Katalogimport

### Added

- `data/curriculum_catalog_v1.csv` um die optionale Spalte `competency_label` und 154 konkrete Arbeitskatalog-Kompetenzen ueber alle aktiven Katalogfaecher ergaenzt.
- Neue konkrete Kompetenzen mit stabilen IDs `CMP-000059` bis `CMP-000212` angelegt; bestehende IDs `CMP-000001` bis `CMP-000058` bleiben erhalten und werden fachlich nicht umgedeutet.
- Tests fuer Katalog-Upsert, leere und bestehende SQLite-Datenbanken, Idempotenz, Bestandsschutz, Fach-Struktur und konkrete Kurzlabels ergaenzt.

### Changed

- Katalogimport in SQLite von Empty-only-Seed auf idempotenten Upsert umgestellt: neue CSV-IDs werden auch in bestehenden lokalen Datenbanken nachgezogen, lokale Nicht-CSV-Kompetenzen bleiben erhalten und vorhandenes `active` wird bei bestehenden IDs nicht aus dem CSV ueberschrieben.
- `CurriculumDesktopAdapter` nutzt `competency_label` fuer kompakte Kompetenzlabels; ohne Spalte oder Wert bleibt die bisherige Fallback-Logik erhalten.
- Projektdokumentation beschreibt den konkreten Sprint-3B-Arbeitskatalog, den Bestandsschutz fuer alte grobe Kompetenzen und den fehlenden Bedarf fuer DB-Schema- oder Beobachtungsdatenmigration.

### Not Changed

- Keine DB-Schema-Migration, keine Beobachtungsdaten-Migration, keine neue Bewertungsskala, kein Status `offen`, keine Qt-Screens, keine Beobachtungsdialog-Hierarchie, keine Dokumentationsstand-Berechnung, keine Berichtsanpassung, keine aktive-Faecher-Logik und kein Commit umgesetzt.
- Die neu ergaenzten konkreten Inhalte sind ein Arbeitskatalog/Entwurf und muessen fachlich von Laura geprueft werden, weil `docs/Lehrplan.md` noch keine detaillierte Lehrplanabbildung enthaelt.

## Sprint 3A - Fachliches Mapping Kompetenzstruktur

### Changed

- Fachliches Mapping der vorhandenen Kompetenzfelder dokumentiert: `subject_id` / `subject_name` = Fach, `learning_area` = Kompetenzbereich, `competency_group` = Thema, `description` / `competency_text` = konkrete Kompetenz und `label` = Kurzlabel fuer kompakte UI.
- Festgehalten, dass Bewertung pro Kompetenz bereits ueber `observation_competency_ratings.rating` je `observation_id` + `competency_id` erfolgt und keine Rating-Schema-Migration fuer Sprint 3 noetig ist.
- Regel dokumentiert: `offen` ist kein gespeicherter Ratingwert; nicht bewertete Kompetenzen erzeugen keine Zeile in `observation_competency_ratings`.
- Bestandsdaten-Regel ergaenzt: alte grobe Kompetenzen bleiben historisch lesbar, alte Beobachtungen werden nicht automatisch auf spaetere konkrete Kompetenzen migriert, und alte Kompetenzen duerfen spaeter deaktiviert oder archiviert, aber nicht geloescht werden.

### Not Changed

- Keine Python-Logik, keine SQLite-Migration, keine CSV-Katalogaenderung, keine UI-Aenderung, keine Testaenderung und kein Commit umgesetzt.

## Sprint 2C - Dokumentationsrelevante Faecher in Auswertungen

### Changed

- Dokumentationsstand und kompakte Dokumentations-Summary beruecksichtigen `documentation_subject_settings`.
- Offene Beobachtungsanlaesse und `missing_competencies` werden nur fuer dokumentationsrelevante Faecher abgeleitet.
- `Im Blick behalten` nutzt fuer Beobachtungshinweise nur noch die aktiven Dokumentationsfaecher.
- Berichtsvorschau behaelt echte Beobachtungen und bestaetigte Kompetenzstaende auch in nicht dokumentationsrelevanten Faechern sichtbar.
- Nacharbeit: Der Beobachtungsdialog bietet fuer neue Beobachtungen nur dokumentationsrelevante Faecher an; bei Bearbeitung bleibt ein inzwischen nicht dokumentationsrelevantes Bestandsfach sichtbar.

### Not Changed

- Keine Settings-UI-Neustruktur ueber eine minimale Hilfetextkorrektur hinaus, keine Datenbankmigration, keine neue Tabelle, keine Kompetenzstruktur-Aenderung, keine Aenderung an `competencies.active`, keine Beobachtungen geloescht, veraendert oder aus Beobachtungslisten versteckt und kein Commit umgesetzt.

## Sprint 2B - Settings-UI dokumentationsrelevante Faecher

### Added

- Einstellungen-Screen um den Abschnitt `Dokumentationsrelevante Faecher` mit Checkboxen, Hilfetext und Speichern-Aktion erweitert.
- Adapter-/ViewModel-Uebersetzung fuer auswaehlbare Dokumentationsfaecher aus aktivem Kompetenzkatalog und `documentation_subject_settings` ergaenzt.
- Tests fuer Default-Auswahl, Persistenz, unveraendertes `competencies.active` und das Settings-Screen-Signal ergaenzt.

### Not Changed

- Keine Filterung von Dokumentationsstand, offenen Kompetenzen, Empfehlungen oder Bericht, keine Beobachtungsdialog-Aenderung, keine Kompetenzstruktur-Aenderung, keine neue Tabelle und kein Commit umgesetzt.

## Sprint 2A - Datenhaltung dokumentationsrelevante Faecher

### Added

- SQLite-Tabelle `documentation_subject_settings` fuer die spaetere Auswahl dokumentationsrelevanter Faecher vorbereitet.
- Repository-/Store-Methoden fuer Lesen, Default und vollstaendiges Speichern aktiver Dokumentationsfaecher ergaenzt.

### Not Changed

- Keine Settings-UI, keine Filterung von Dokumentationsstand, offenen Kompetenzen oder Bericht, keine Beobachtungsdialog-Aenderung, keine Kompetenzkatalog-Aenderung, keine aktive-Faecher-Logik in Qt-Screens und kein Commit umgesetzt.

## Sprint 1B-3 - H02 Kompetenzbestaetigung sichtbar machen

### Changed

- Kompetenzuebersicht ergaenzt bestaetigte Kompetenzstaende ohne aktive Beobachtungshistorie aus `student_competency_confirmations`.
- Berichtsvorschau nutzt diese bestaetigten Kompetenzstaende ueber die bestehende Kompetenzuebersicht und erzeugt fuer bestaetigungsreine positive Staende keine kuenstliche Entwicklungslinie.
- Nacharbeit: Berichtsvorschau zeigt je relevanter Kompetenz den aktuellen Stand mit Quelle getrennt von Entwicklung/Verlauf.
- Nach Soft Delete der zugrunde liegenden Beobachtung bleibt ein bestaetigter Kompetenzstand sichtbar und berichtsrelevant.

### Not Changed

- Keine Datenbankmigration, keine neue Kompetenzstruktur, keine Bewertung pro konkreter Kompetenz, keine aktive-Faecher-Logik, keine Berichtsgrafiken, kein Dashboard, kein UI-Redesign, kein neuer Application-Command und kein Commit umgesetzt.

## Sprint 1B-2 - K02 Dokumentationsdetails zugänglich machen

### Changed

- Schuelerprofil zeigt im bestehenden Dokumentationsstand-Detailsbereich pro Fach Fachname, Zaehler, Fortschrittstext und ruhige Hinweise fuer naechste Beobachtungen.
- Nacharbeit: Der Dokumentationsstand im Reiter `Überblick` bietet ebenfalls `Details anzeigen` und klappt dieselben ruhigen Fachdetails direkt im Überblick auf.
- Dokumentationshinweise verwenden `Noch wenig belegt` und `Für nächste Beobachtungen geeignet` statt defizitorientierter Detailtexte.

### Not Changed

- Keine H02-Kompetenzbestaetigung, keine aktive-Faecher-Logik, keine neue Kompetenzstruktur, keine Bewertung pro konkreter Kompetenz, keine Berichtsgrafiken, kein Dashboard, keine Datenbankaenderung, keine Adapterlogik und kein Commit umgesetzt.

## Sprint 1B-1 - Laura-Test-Fix J04 Dateien entfernen

### Added

- Schuelerprofil zeigt im Reiter `Dateien` pro Dokument eine ruhige Aktion `Entfernen`.
- Entfernen nutzt die bestehende Soft-Delete-Logik ueber `documents.active = 0`; physische Dateien bleiben im Dateisystem.

### Not Changed

- Keine Datenbanktabelle, keine Migration, keine physische Dateiloeschung, keine H02-Kompetenzbestaetigung, keine K02-Dokumentationsdetails, kein UI-Redesign, kein Dashboard und kein Commit umgesetzt.

## Sprint 1A - Laura-Test-Fixes / UX-Stabilisierung

### Changed

- Beobachtungs-Speichern nutzt keine blockierende Erfolgsmeldung mehr; die App zeigt nach Speichern, Bearbeiten und Loeschen ruhig im bestehenden Statusbereich, welcher Kontext erhalten bleibt.
- Nacharbeit H01: Nach erfolgreichem Anlegen oder Bearbeiten steht im Shell-Statusbereich wieder die klare Erfolgsmeldung `Beobachtung wurde gespeichert.` bzw. `Beobachtung wurde aktualisiert.`.
- Kompetenzstatus-Texte verwenden ruhigere Begriffe wie `Vorschlag aus Beobachtungen`, `aus Beobachtungen abgeleitet`, `von Laura bestätigt`, `aktuell bestätigt` und `noch nicht bestätigt`.
- Bestehende Beobachtungs-, Kompetenzgruppen- und Dokumentkarten sind zusätzlich zur vorhandenen Details-/Oeffnen-Schaltflaeche klickbar.

### Not Changed

- Keine fachliche Kompetenzlogik, keine Datenmodell- oder SQLite-Schemaaenderung, keine neue Detailansicht, keine Dateien-entfernen-Funktion, kein Dashboard, keine Berichtsgrafiken, kein Excel-/VBA-Bezug und kein Commit umgesetzt.

## Sprint - Schuelerprofil-Ueberblick vor Laura-Pilottest

### Added

- Schuelerprofil startet mit dem Reiter `Überblick` und einer kompakten Karte `Halbjahresblick`.
- Der Überblick zeigt aktive Beobachtungen, Dokumentationsstand, letzte aktive Beobachtung, abgeleitete Stärken, Beobachtungshinweise und sichtbare Entwicklung.
- Das Profil ist in die Reiter `Überblick`, `Beobachtungen`, `Kompetenzen`, `Bericht` und `Dateien` gegliedert.

### Changed

- Bestehende Beobachtungen, Kompetenzdetails, Berichtsvorschau und Dokumente bleiben erhalten, werden aber aus dem ersten Profilblick herausgenommen.
- Laura-Pilottestpunkte zum Schuelerprofil wurden auf Orientierung, Halbjahresblick und Reiterstruktur ausgerichtet.

### Not Changed

- Keine neue Persistenz, keine Schemaaenderung, keine SQLite-Logik in Qt-Screens, keine Beobachtungs-/Kompetenzlogik entfernt, kein Excel-/VBA-Bezug und kein Commit umgesetzt.

## Sprint - Schnellbeobachtung und Zurueck-Navigation

### Added

- Schuelerlisten erhalten pro Schueler eine kompakte Zeilenaktion `Beobachten`.
- Gefilterte Schuelerlisten fuer Stammgruppen, Kurse und Kursverbuende erhalten `← Zur Übersicht`.

### Changed

- Schnellbeobachtung nutzt den bestehenden `NewObservationDialog` und aktualisiert nach dem Speichern Liste, Uebersicht und Dokumentationsstatus.

### Not Changed

- Keine neue Beobachtungslogik, keine Datenmodell- oder Schemaaenderung, keine direkte SQLite-Logik in Qt-Screens, kein Excel-/VBA-Bezug und kein Commit umgesetzt.

## Sprint - Excel/VBA-Legacy bereinigen

### Changed

- Reine Excel-/openpyxl-/VBA-Altstaende in `legacy/excel/` archiviert.
- Alter Excel/VBA-CLI-Bridge-Adapter `km.py` samt Runtime-Adapter-Test in das Legacy-Archiv verschoben.
- Aktive PySide-/SQLite-Referenzdaten aus Workbook-Abhaengigkeiten geloest und in `src/core/records.py` gefuehrt.
- README und Governance-Dokumente auf PySide/SQLite als einzigen aktiven Hauptpfad und neue Standardchecks ohne Excel-Build aktualisiert.

### Removed

- `openpyxl` aus den aktiven Runtime-Abhaengigkeiten entfernt.
- Versionierter Platzhalter `output/.gitkeep` entfernt, weil `output/` Runtime-/Exportbereich bleibt.

### Not Changed

- Keine PySide-Fachlogik geaendert, keine SQLite-Schemaaenderung, keine Runtime-Dateien versioniert und kein Commit umgesetzt.

## Sprint - Berichtsvorschau und Halbjahres-Testdaten

### Changed

- Berichtsvorschau leitet den Bereich `Entwicklung` aus chronologischen aktiven Beobachtungen ab.
- Entwicklung zeigt verstaendliche Hinweise fuer Einzelbeobachtung, stabile Verlaeufe, positive Entwicklung, Rueckschritt und wechselnde Beobachtungslage.
- Leere Berichtsvorschau verwendet `Noch keine Beobachtungen dokumentiert.` statt unklarer Berichtsdaten- oder Entwicklungseintraege.
- `scripts/seed_test_data.py` erzeugt realistischere Halbjahresdaten von September bis Januar mit mehreren Beobachtungen je Testschueler, Verlaufsmustern, Bestaetigungen und Demo-Dokumenten.

### Not Changed

- Keine KI-Textgenerierung, keine finalen Zeugnisformulierungen, keine Schemaaenderung, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Dokumentationsstatus kompakt in Schuelerlisten

### Changed

- Schuelerlisten zeigen einen kompakten Dokumentationsstatus je Schueler, ohne vollstaendige Fachaufschluesselung.
- Schuelerprofil zeigt den Dokumentationsstand zuerst als kompakte Lernbereich-Summary; Fachdetails sind per `Details anzeigen` aufklappbar.
- Dokumentationsstatus zaehlt dokumentierte Lernbereiche je Fach; aktive Beobachtungen und bestaetigte Kompetenzstaende zaehlen, Soft Deletes nicht.

### Not Changed

- Keine neue Persistenz, keine Schemaaenderung, keine SQLite-Logik in Qt-Screens, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Laura-Pilottestdaten fuer SQLite

### Added

- Script `scripts/seed_test_data.py` erzeugt kuenstliche Testdaten fuer `data/kompetenzmanager.sqlite`.
- Testdaten decken Stammgruppen, Kurse, Kursverbuende, Schueler, Beobachtungen, Kompetenzvorschlaege, bestaetigte Kompetenzstaende, Berichtsvorbereitung, Dokumentationsstand sowie Dokumente & Medien ab.
- `--reset` erzeugt bewusst ein frisches lokales Testsystem inklusive Demo-Dateien unter `data/documents/`.

### Not Changed

- Kein Excel-/VBA-Umbau, keine echten Namen, keine echten Dokumente und kein Commit umgesetzt.

## Sprint - Dokumente & Medien MVP

### Added

- SQLite-Metadaten fuer Dokumente und Medien mit studentenzentrierter Dateiablage unter `data/documents/<student_id>/`.
- Beobachtungsdialog kann Dateien als Beobachtungsanhaenge hinzufuegen und beim Bearbeiten entfernen.
- Schuelerprofil zeigt aktive Dokumente und Medien des Schuelers sowie Beobachtungsanhaenge in aufgeklappten Beobachtungskarten.
- Dateien koennen aus dem Schuelerprofil ueber das Betriebssystem geoeffnet werden, wenn ein Dateipfad vorhanden ist.

### Not Changed

- Keine PDF-Erstellung, keine Bild-/Audio-Vorschau, keine Datei-BLOBs in SQLite, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Dokumentationsstand im Schuelerprofil

### Added

- Schuelerprofil zeigt einen kompakten Dokumentationsstand pro Fach aus Kompetenzkatalog, aktiven Beobachtungen und bestaetigten Kompetenzstaenden.
- Fach-Kompetenzgruppen koennen noch nicht dokumentierte Kompetenzen optional aufklappen.

### Not Changed

- Keine neue Persistenz, keine Schemaaenderung, keine Dokumentenverwaltung, keine Berichtserweiterung, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Berichtsvorschau kopieren und als Text exportieren

### Added

- Berichtsvorschau im Schuelerprofil kann als strukturierter Text in die Zwischenablage kopiert werden.
- Berichtsvorschau kann als einfache `.md`- oder `.txt`-Datei exportiert werden.
- Textausgabe enthaelt Schuelername, Stammgruppe, Kurs, Erstellungsdatum, Fachgruppen, Kompetenzstaende und Beobachtungsbelege.

### Not Changed

- Keine PDF-/Word-Erstellung, keine KI-Textgenerierung, keine finalen Zeugnisformulierungen, keine neue Persistenz, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint B - Berichtsvorbereitung aus Kompetenzstaenden und Beobachtungen

### Added

- Berichtsvorschau im Schuelerprofil als strukturierte Lernentwicklungsuebersicht nach Fach ergaenzt.
- Berichtsvorschau nutzt bestaetigte Kompetenzstaende, falls vorhanden, sonst den berechneten Vorschlag.
- Aktive Beobachtungen werden als Beispielbelege je Fach angezeigt.

### Not Changed

- Keine KI-Textgenerierung, keine finalen Zeugnisformulierungen, kein PDF-/Word-Export, keine neue Persistenz, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint A - Bestaetigten Kompetenzstand speichern

### Added

- SQLite-Tabelle `student_competency_confirmations` fuer bestaetigte Kompetenzstaende der Lehrkraft ergaenzt.
- Kompetenzuebersicht im Schuelerprofil kann den berechneten Vorschlag uebernehmen oder manuell bestaetigen.
- Bestaetigter Stand bleibt nach Reload erhalten und wird neben dem Vorschlag angezeigt.

### Changed

- Kompetenzzeilen zeigen `Vorschlag`, `noch nicht bestätigt` oder `Bestätigt` inklusive Abweichung zwischen Vorschlag und bestaetigtem Stand.
- Bei neuerer Beobachtung nach einer Bestaetigung wird sichtbar, dass ein neuerer Vorschlag vorhanden ist.

### Not Changed

- Beobachtungen bleiben unveraendert, berechnete Vorschlaege werden weiterhin abgeleitet, keine Berichte, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Kompetenzvorschlag und aufklappbare Fachgruppen im Schuelerprofil

### Changed

- Kompetenzuebersicht im Schuelerprofil zeigt Faecher als kompakte aufklappbare Zeilen.
- Pro Kompetenz wird der berechnete Stand als `Vorschlag` angezeigt, nicht als endgueltige Lehrerentscheidung.
- Vorschlag wird aus aktiven Beobachtungen als gewichteter Mittelwert berechnet; neuere Bewertungen zaehlen staerker, aeltere bleiben beruecksichtigt.
- Pro Kompetenz werden Verlauf, Anzahl der Beobachtungen und Datum der neuesten aktiven Beobachtung angezeigt.
- Backlogpunkt fuer spaeteres Bestaetigen oder manuelles Anpassen des Vorschlags durch die Lehrkraft ergaenzt.

### Not Changed

- Kein Speichern berechneter Kompetenzstaende, keine Schemaaenderung, keine Diagramme, keine Berichte, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Kursverbund anlegen und Schuelerlisten sortieren

### Added

- Button `+ Kursverbund` in den PySide-Stammdaten angebunden.
- Neue Kursverbuende koennen mit Name, Stammgruppen und Kursen ueber den bestehenden Kursverbund-Dialog persistent in SQLite angelegt werden.
- Duplikate mit gleichem Kursverbundnamen werden UI-nah abgefangen.

### Changed

- Schuelerlisten werden zentral nach Kursreihenfolge und danach alphabetisch nach Schuelername sortiert.
- Kurs-, Stammgruppen- und Kursverbundfilter nutzen dieselbe sortierte Datenquelle.

### Not Changed

- Keine Schemaaenderung, keine Beobachtungspersistenz, keine Medien, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## UI-Polish - Beobachtungsverlauf im Schuelerprofil beruhigen

### Changed

- Schuelerprofil zeigt ohne aktive Filter standardmaessig nur die drei neuesten Beobachtungen.
- Bei mehr Beobachtungen kann der Verlauf ueber `Alle Beobachtungen anzeigen (X)` erweitert und ueber `Weniger anzeigen` wieder reduziert werden.
- Details-, Reset- und Filteraktionen sind optisch dezenter an das App-Theme angepasst.
- Bewertungsfilter, Fachfilter und Suche sind proportional ruhiger gestaltet; der verbesserte ComboBox-/Dropdown-Stil gilt app-weit.
- Datum-, Zeit- und Datum-Zeit-Felder nutzen app-weit denselben ruhigen Dropdown-/Indicator-Stil.

### Not Changed

- Keine Persistenz- oder Schemaaenderung, keine Aenderung der Kompetenzuebersicht, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## UI-Polish - Beobachtungen im Schuelerprofil filtern

### Added

- Schuelerprofil filtert den Beobachtungsverlauf lokal nach Fach, Bewertung und Suchtext.
- Reset-Button setzt Fach, Bewertung und Suche auf `Alle` beziehungsweise leer zurueck.

### Not Changed

- Keine Persistenz- oder Schemaaenderung, keine Aenderung der Kompetenzuebersicht, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## UI-Polish - Aufklappbare Beobachtungskarten

### Changed

- Beobachtungen im Schuelerprofil starten kompakt mit Datum, Fach, Kontext, Notizvorschau und Kompetenzanzahl.
- Detailbereich wird per `Details anzeigen` geoeffnet und zeigt volle Notiz, Kompetenzbewertungen sowie Bearbeiten/Loeschen.

### Not Changed

- Keine Persistenz- oder Schemaaenderung, keine Aenderung der Kompetenzuebersicht, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Beobachtungen bearbeiten und löschen

### Added

- Schuelerprofil bietet pro Beobachtung Aktionen zum Bearbeiten und Loeschen.
- Beobachtungen koennen mit Datum, Kontext, Notiz, Kompetenzen und Bewertungen aktualisiert werden.
- Loeschen ist als Soft Delete ueber `observations.active = 0` umgesetzt.

### Changed

- Kompetenzuebersicht wird nach Bearbeiten oder Loeschen aus den aktiven Beobachtungen neu abgeleitet.
- Multi-Fach-Beobachtungen berechnen das Profil-Fachlabel nach dem Bearbeiten erneut aus den Kompetenzfaechern.

### Not Changed

- Keine Medien, keine Berichte, kein UI-Redesign, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Kompetenzen SQLite-persistent machen

### Added

- SQLite-Tabelle `competencies` fuer den seedbaren Kompetenzkatalog ergaenzt.
- Kompetenzkatalog wird aus `data/curriculum_catalog_v1.csv` nur bei leerer `competencies`-Tabelle geseedet.
- Schuelerprofil zeigt eine aus Beobachtungen abgeleitete Kompetenzuebersicht je Fach mit letzter Bewertung und letztem Beobachtungsdatum.

### Not Changed

- Keine freie Kompetenzbearbeitung, keine doppelte manuelle Kompetenzstand-Speicherung, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Kompetenzkatalog fachlich stabilisieren

### Changed

- `data/curriculum_catalog_v1.csv` fuehrt `competency_id` jetzt explizit als stabile Katalog-ID.
- Curriculum-Adapter validiert Pflichtfelder und doppelte Kompetenz-IDs und bietet eine Fach-Gruppierung fuer Kompetenzen.
- EPU bleibt sichtbarer Fachname; Sozialkompetenz bleibt eigener Katalogbereich.

### Not Changed

- Keine freie Kompetenzbearbeitung, keine Schema-Migration, kein Excel-/VBA-Umbau, keine UI-Grossbaustelle und kein Commit umgesetzt.

## Korrektur - Multi-Fach-Beobachtungen im Schuelerprofil

### Changed

- Fachanzeige im Schuelerprofil wird aus den Faechern der gespeicherten Kompetenzbewertungen abgeleitet.
- Beobachtungen mit Kompetenzen aus mehreren Faechern zeigen `Fächerübergreifend`; einzelne Kompetenzen behalten ihr eigenes Fachlabel.

### Not Changed

- Keine Schema-Migration, keine Aenderung gespeicherter Kompetenzbewertungen, keine SQLite-Zugriffe im Screen/Dialog und kein Excel-/VBA-Umbau umgesetzt.

## UI-Polish - Schuelerprofil Beobachtungsliste

### Changed

- Persistente Beobachtungen im Schuelerprofil werden als kompakte Karten mit Datum, Fach, Kontext, Notiz und Kompetenzbewertungen angezeigt.
- Empty State der Beobachtungsliste auf den persistenten Stand aktualisiert.

### Not Changed

- Keine Persistenz-, Schema-, SQLite-, Excel-/VBA- oder Packaging-Aenderung umgesetzt.

## Sprint - Beobachtungen persistent speichern

### Added

- SQLite-Schema um `observations` und `observation_competency_ratings` erweitert.
- `SQLiteObservationRepository`, `ObservationService` und `observation.create` fuer persistente Beobachtungen ergaenzt.
- Schuelerprofil laedt gespeicherte Beobachtungen nach Adapter-/App-Neustart wieder aus SQLite.

### Changed

- Beobachtungsdialog speichert Datum, Fach, Kontext, Notiz und mehrere kompetenzbezogene Bewertungen ueber den Adapter-/Service-/Repository-Pfad.
- Rating-Werte werden stabil als `++`, `+`, `-` und `--` gespeichert.

### Not Changed

- Keine Medien/Anhaenge, keine Berichte/Auswertungen, kein Export, kein Packaging, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - Schuelerdaten persistent speichern und laden

### Changed

- Produktiver PySide-App-Start initialisiert eine fehlende SQLite-Datenbank mit Schema, Stammdaten und Kursverbund-Defaults, aber ohne Demo-Schueler.
- Neu angelegte Schueler werden ueber den bestehenden `student.create`-Pfad in SQLite gespeichert und nach Adapter-/App-Neustart wieder geladen.
- Schuelerliste, Suche, Schuelerprofil, Stammgruppenfilter und Kursverbundfilter nutzen weiterhin persistente `student_id`, `group_id` und `course_id`.

### Not Changed

- Keine Beobachtungspersistenz, keine Bewertungen, keine Medien, keine Berichte, kein Packaging, kein UI-Redesign und kein Excel-/VBA-Umbau umgesetzt.

## Sprint - Stammdaten und Kursverbuende persistent speichern

### Added

- SQLite-Schema um Kursverbund-Tabellen und Relationen zu Stammgruppen und Kursen erweitert.
- Persistenten `SQLiteMasterDataRepository` fuer Stammgruppen, Kurse, Kursfarben und Kursverbuende ergaenzt.
- Defaults fuer Stammgruppen, Kurs 1/2/3 und `Mathe/Deutsch Kursverbund A` werden nur bei leerem Stammdaten-Scope erzeugt.

### Changed

- `MasterDataDesktopAdapter` speichert neue und umbenannte Stammgruppen, Kurse und Kursverbund-Aenderungen dauerhaft in SQLite.
- Kursfarben werden mit Name und Hex-Wert in SQLite gehalten.
- Stammdaten-UI bleibt optisch unveraendert; nur Speichern/Laden ist persistent.

### Not Changed

- Keine Beobachtungspersistenz, keine Medien, keine Berichte, kein Packaging, kein Installer, kein Excel-/VBA-Umbau und kein Commit umgesetzt.

## Sprint - PySide Icon Branding und Glas-Polish

### Added

- App-Icon als versioniertes Asset `assets/app_icon.png` ergaenzt.
- Zentralen PySide-Asset-Helfer `src/desktop_app/assets.py` fuer Icon-Pfad, Pixmap-Laden und Icon-Label ergaenzt.
- App-Icon oben in der Seitenleiste und oben zentriert im App-Info-Dialog sichtbar eingebunden.

### Changed

- Zentrales PySide-Theme um etwas weichere Karten-, Panel-, Eingabe- und Sidebar-Polish-Regeln ergaenzt.
- Leichte Glasoptik wird weiter nur hell, dezent und lesbar simuliert.

### Not Changed

- Keine Fachlogik, keine Persistenz, keine SQLite-Aenderung, kein Excel-/VBA-Umbau, kein Packaging, kein Installer und kein Commit umgesetzt.

## Sprint - PySide Icon Theme

### Changed

- Zentrales PySide-Theme `src/desktop_app/theme.py` aus der freigegebenen Icon-Farbwelt ergaenzt.
- App-weites Stylesheet fuer Navigation, Karten, Tabellen, Eingaben, Buttons und Dialogflaechen angebunden.
- Bestehende PySide-Screens und Dialoge auf semantische Theme-Helfer fuer Titel, Karten, Hinweise und Fehlermeldungen umgestellt.
- Primäre Dialogbuttons nutzen weiterhin die freigegebene blaue Aktionsfarbe, jetzt aus dem zentralen Theme.

### Not Changed

- Keine Fachlogik, keine neue Persistenz, keine SQLite-Aenderung, keine Beobachtungspersistenz, kein ObservationRepository, kein Excel-/VBA-Umbau, kein Packaging und kein Curriculum-Umbau umgesetzt.

## Sprint - PySide Kursverbund bearbeiten

### Changed

- Kursverbuende koennen in den Stammdaten session-lokal bearbeitet werden.
- Dialog `Kursverbund bearbeiten` mit Name, Stammgruppen-Checkboxen und Kurs-Checkboxen ergaenzt.
- Kursverbund-Filter bleibt kursverbundbezogen: Kurs plus ausgewaehlte Stammgruppen.
- Stammdaten- und Uebersichtsseite nutzen die aktualisierte session-lokale Kursverbund-Auswahl.
- Schueleruebersicht bleibt mit Kurs-Spalte, farbigem Marker und neutralem Kursnamen erhalten.

### Not Changed

- Keine SQLite-Persistenz fuer Kursverbuende, keine Migration, kein Repository, keine Beobachtungspersistenz, kein Excel-/VBA-Umbau, kein Packaging und kein Commit umgesetzt.

## Architektur-Sprint - PySide Hauptanwendung, Excel/VBA Legacy/Export

### Changed

- ADR-046 ergaenzt: PySide ist Hauptanwendung, SQLite ist produktive lokale Datenbasis, Excel/VBA ist Legacy-/Export-/Referenzpfad.
- README, PROJECT, ROADMAP, AGENTS und Governance-Dokumente auf PySide-/SQLite-Zielbild bereinigt.
- Excel/openpyxl als Export-/Legacy-Kontext eingeordnet, nicht mehr als Haupt-App-Startweg.
- VBA als Zielpfad fuer neue Features, UI, Smoke-Tests, Automatisierung und produktive Workflows ausgeschlossen.
- PySide6-App-Feasibility als erfolgreich abgeschlossene Machbarkeitsphase markiert.

### Not Changed

- Keine Produktlogik, keine UI-Aenderung, keine SQLite-Migration, kein Packaging, kein Installer, kein PyInstaller, keine Excel-/VBA-Code-Loeschung und kein Commit umgesetzt.

## Korrektur-Hotfix - PySide Kursverbuende und Schuelerliste

### Changed

- Speichern-Buttons in PySide-Dialogen nutzen zentral einen blauen Primary-Stil.
- Kursfarben-Palette um Gelb `#EAB308` erweitert.
- PySide-Schuelerliste zeigt wieder eine saubere Kurs-Spalte mit farbigem Marker und neutralem Kursnamen.
- Kaputte Kursmarker-/Text-Ueberlagerung in der Schuelerliste repariert, ohne Kursverbund-Filterlogik zurueckzubauen.
- Session-lokalen Kursverbund `Mathe/Deutsch Kursverbund A` im Stammdaten-/Uebersichts-Scope ergaenzt.
- PySide-Uebersicht `Stammgruppen und Schülerbestand` zeigt Stammgruppen sowie Kurse innerhalb des Kursverbunds.
- Kursfilter aus der Uebersicht filtert nach Kurs und den Stammgruppen des ausgewaehlten Kursverbunds.
- UX-Backlogpunkt ergaenzt: Kompetenznamen in der Beobachtungs-Bewertungsliste spaeter auf moegliche Fettung pruefen.

### Not Changed

- Keine neue Persistenz, keine SQLite-Aenderung, keine Beobachtungspersistenz, kein ObservationRepository, kein Excel-/VBA-Umbau, keine Packaging-Toolchain, keine produktive Kursverbund-Bearbeitung und keine Fettung der Kompetenznamen umgesetzt.

## Dokumentation - Icon-basierte visuelle Leitlinie

### Changed

- App-Icon als zentrale gestalterische Referenz fuer die PySide-Hauptanwendung dokumentiert.
- Farbwelt, Formensprache, Bedeutungsanker und leichte moderne Glasoptik fuer kuenftige Screens festgehalten.
- PySide als kuenftige Hauptanwendung dokumentiert; Excel/VBA bleibt Export-, Berichts- oder Legacy-Projektion.

### Not Changed

- Keine Codeaenderung, kein Build, kein Commit, keine neue Persistenz, keine SQLite-Aenderung, kein Excel-/VBA-Umbau und keine Fachlogik umgesetzt.

## Hotfix - macOS-Launcher fuer PySide6-Prototyp

### Added

- Doppelklick-faehigen macOS-Launcher `launcher/Jenaplan_Kompetenzmanager.command` fuer den PySide6-Prototyp ergaenzt.
- Startanleitung fuer Terminalstart und Launcherstart in `README.md` ergaenzt.
- Kleinen Smoke-Test fuer Existenz, Ausfuehrbarkeit und Startmodul des Launchers ergaenzt.

### Not Changed

- Kein PyInstaller, keine `.app`-Bundle-Erzeugung, kein Installer, keine neue Persistenz, keine SQLite-Aenderung, keine Fachlogik, kein Excel-/VBA-Umbau und keine Curriculum-Aenderung umgesetzt.

## Sprint - PySide6 UI-Polish

### Changed

- Speichern-/Abbrechen-Buttons in PySide6-Dialogen vereinheitlicht.
- Empty States fuer Schuelerliste und Stammdaten-Seite ergaenzt.
- App-Info-Dialog mit nicht-technischen Prototyp-Hinweisen ergaenzt.
- Suchfeld in der Schuelerliste auf `Schüler suchen …` und `Zurücksetzen` verfeinert.
- Dialoge fuer einfachen Tastaturkomfort mit Default-Speichern und Esc-Abbrechen vorbereitet.

### Not Changed

- Keine Fachlogik, keine neue Persistenz, keine SQLite-Aenderung, keine Beobachtungspersistenz, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Curriculum-Katalog-Umbau, kein Excel-/VBA-Umbau, kein Packaging und keine finale Architekturentscheidung umgesetzt.

## Hotfix - PySide6 Kursfarben anzeigen

### Changed

- Kurse im Stammdaten-light-ViewModel fuehren eine UI-Farbe als Name und Hex-Wert.
- Kursdialoge bieten eine feste Farbauswahl fuer Blau, Gruen, Orange, Lila, Rot und Grau.
- Stammdaten-Seite zeigt Kursfarben als kleinen Farbmarker in der Kursliste.
- PySide6-Schuelerliste zeigt die Kursfarbe als kleinen Marker neben dem Kursnamen.

### Not Changed

- Keine neue Persistenz fuer Kursfarben, keine SQLite-Aenderung, keine Beobachtungspersistenz, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Curriculum-Katalog-Umbau, kein Excel-/VBA-Umbau, kein Packaging und keine finale Architekturentscheidung umgesetzt.

## Sprint - PySide6 Schuelerdialog an Stammdaten anbinden

### Changed

- PySide6-Dialog `Neuer Schüler` nutzt die Stammdaten-light-Quelle fuer Stammgruppen- und Kursauswahl.
- Stammgruppen- und Kursauswahl zeigen `Bitte auswählen` als Platzhalter und vermeiden Freitext.
- Leerer Name, fehlende Stammgruppe und fehlender Kurs werden vor dem Speichern mit verstaendlichen Meldungen abgefangen.
- Session-lokale Stammdaten aus `MasterDataDesktopAdapter` sind im Dialog sichtbar; nur dauerhaft vorhandene Stammgruppen/Kurse koennen fuer `student.create` verwendet werden.

### Not Changed

- Keine neue Persistenz, keine produktive Stammgruppen-/Kurspersistenz, keine Schueler-Umbuchung, keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Curriculum-Katalog-Umbau, kein Excel-/VBA-Umbau, kein Packaging und keine finale Architekturentscheidung umgesetzt.

## Sprint - PySide6 Stammdaten light

### Added

- PySide6-Navigation um `Stammdaten` erweitert.
- Nicht-persistente Stammdaten-light-Seite fuer Stammgruppen und Kurse ergaenzt.
- Dialoge fuer neue Stammgruppen, neue Kurse und Umbenennen mit einfacher Leerfeld-Validierung ergaenzt.
- GUI-naher Stammdaten-Adapter liest bestehende Gruppen/Kurse aus der vorhandenen Datenquelle und verwaltet Aenderungen nur session-lokal.

### Not Changed

- Keine produktive Stammgruppen-/Kurspersistenz, keine Schueler-Umbuchung, kein Loeschen, keine Beobachtungspersistenz, keine SQLite-Aenderung fuer Beobachtungen, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Curriculum-Katalog-Umbau, kein Excel-/VBA-Umbau, kein Packaging und keine finale Architekturentscheidung umgesetzt.

## Hotfix - Beobachtungsdialog faecheruebergreifende Kompetenzbewertungen

### Changed

- Fachwechsel im PySide6-Beobachtungsdialog erhaelt bereits ausgewaehlte Kompetenzbewertungen.
- Das Fach-Dropdown filtert nur noch die sichtbare Kompetenzauswahl und ist keine globale Fachbindung der Beobachtung.
- Kompetenzbewertungszeilen zeigen den Fach-Anzeigenamen und koennen direkt entfernt werden.
- Nicht-persistenter Observation-Draft fuehrt `subject_key` und `subject_display_name` pro Kompetenzbewertung.

### Not Changed

- Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Excel-/VBA-Umbau, kein Packaging und keine finale Architekturentscheidung umgesetzt.

## Sprint - Beobachtungsdialog Bewertung pro Kompetenz

### Changed

- Globale Bewertung im PySide6-Beobachtungsdialog entfernt.
- Nicht-persistenter Observation-Draft fuehrt Bewertungen pro ausgewaehlter Kompetenz.
- Dialog zeigt fuer jede ausgewaehlte Kompetenz eine eigene Bewertungs-Auswahl.
- Fachwechsel und Abwaehlen einer Kompetenz setzen die zugehoerigen Draft-Bewertungen zurueck.
- Dialoginhalt in eine ScrollArea gelegt, damit die Buttonleiste auch bei vielen ausgewaehlten Kompetenzen erreichbar bleibt.
- Kompetenzauswahl und Bewertungszeilen kompakter gestaltet.

### Not Changed

- Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Excel-/VBA-Umbau, kein Packaging und keine finale Architekturentscheidung umgesetzt.

## Hotfix - Beobachtungsdialog Kompetenzauswahl lesbarer

### Changed

- Kompetenzauswahl im PySide6-Beobachtungsdialog auf kurze Lernbereich-Labels umgestellt.
- Kompetenzliste als sichtbare Checkbox-Liste mit Hinweis `Mehrfachauswahl möglich` dargestellt.
- Nicht-persistenter Observation-Draft behaelt die stabilen Kompetenzwerte aus dem Katalog intern bei.

### Not Changed

- Lange Kompetenztexte im Katalog bleiben erhalten. Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Excel-/VBA-Umbau und kein Packaging umgesetzt.

## Sprint - Curriculum-Katalog v1

### Added

- Read-only-Katalog `data/curriculum_catalog_v1.csv` fuer den PySide6-Beobachtungsdialog ergaenzt.
- Curriculum-Adapter `CurriculumDesktopAdapter` zum Laden aktiver Faecher und fachbezogener Kompetenzeintraege ergaenzt.
- Beobachtungsdialog nutzt Fach- und Kompetenzlisten aus dem Katalog statt lokaler Dummy-Listen.
- EPU als App-Anzeigename fuer `Epochaler Projektunterricht` modelliert; offizielle Quelle ist `Heimat- und Sachkunde`.
- Erweiterte Faecher `Ethik`, `Religion`, `Werken` und `Schulgarten` aufgenommen.

### Not Changed

- Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository, keine Dokumenten-/Medienpersistenz, kein Excel-/VBA-Umbau, kein Packaging, kein Berichtsexport und keine finale Architekturentscheidung umgesetzt.

## Sprint - PySide6 Beobachtungsdialog UX-Prototyp 1

### Added

- Nicht-persistenten PySide6-Dialog `Neue Beobachtung` als UX-Prototyp ergaenzt.
- `+ Beobachtung` im Schuelerprofil oeffnet den Dialog im Kontext des ausgewaehlten Schuelers.
- Dialogfelder fuer Datum, Fach, Kompetenz(en), Kontext, Bewertung, Notiz sowie `Dokumente & Medien` ergaenzt.
- Nicht-produktive Hinweise fuer Speichern und `Datei hinzufügen` ergaenzt.
- Lokale UI-Listen fuer Fach und Kompetenzen als Spike-Einschraenkung verwendet, weil noch keine saubere PySide6-Datenquelle fuer diese Auswahl freigegeben ist.

### Not Changed

- Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein Beobachtungs-Repository, keine Datenmodelländerung, keine Dokumentenanhaenge, kein Excel-/VBA-Umbau, kein Packaging, kein Berichtsexport und keine finale Architekturentscheidung umgesetzt.

## Sprint - PySide6 Schuelerprofil UX-Ausbau 1

### Added

- Schuelerprofil als erste Arbeitsseite mit Profilkopf, Basisdaten, Schnellaktionen und Karten fuer Beobachtungen, Kompetenzen und Dokumente ausgebaut.
- Dezente Anzeige der `student_id` im Profilkopf ergaenzt.
- Inline-Hinweise fuer die spaeteren Aktionen `+ Beobachtung`, `Dokument hinzufügen` und `Schüler bearbeiten` ergaenzt.
- Zentrale Platzhaltertexte fuer Beobachtungen, Kompetenzen und schuelerzentrierte Dokumente ergaenzt.

### Not Changed

- Keine Beobachtungsmaske, keine Beobachtungspersistenz, keine Dokumentenverwaltung, keine Kompetenzberechnung, keine Datenmodelländerung, kein Packaging, kein Excel-Export-Umbau und keine finale Architekturentscheidung umgesetzt.

## Sprint - PySide6 UX Stabilisierung 1

### Added

- Zurueck-Button `← Zurück zur Schülerliste` im Schuelerprofil light ergaenzt.
- Suchfeld `Schüler suchen...` in der Schueleruebersicht ergaenzt.
- Testbare Navigationsziel-Aufloesung fuer die Seitenleiste ergaenzt.
- Testbare Schuelerlisten-Filterlogik fuer Vorname, Nachname, Vollname, Stammgruppe und Kurs ergaenzt.
- Nicht-modale Statusmeldung nach erfolgreichem Speichern eines neuen Schuelers ergaenzt.

### Changed

- Schuelerprofil light optisch in Kopfbereich, Notizkarte und Beobachtungsplatzhalter gegliedert.
- Klick auf `Schüler` in der linken Navigation fuehrt auch aus dem Profil wieder sauber zur Schuelerliste.
- Ruecksprung aus dem Profil erhaelt den aktuellen Gruppenfilter.
- Suchtext bleibt beim Ruecksprung aus dem Profil erhalten und filtert innerhalb des aktuellen Gruppenfilters.

### Not Changed

- Keine finale Architekturentscheidung, kein Packaging, keine Beobachtungsmaske, keine Dokumentenverwaltung, kein Excel-Export-Umbau und keine Datenmodelländerung umgesetzt.

## Sprint - PySide6 MVP Shell und Navigation

### Added

- PySide6-App-Shell mit Hauptfenster, linker Navigation und Screen-Stack ergaenzt.
- Uebersicht mit Stammgruppen-/Gruppenkarten und Schuelerzaehlern ergaenzt.
- Schuelerseite mit bestehender SQLite-Schuelerliste und integriertem `+ Schüler`-Dialog ergaenzt.
- Schuelerprofil light mit Name, Stammgruppe, Kurs, Notiz und Platzhalter fuer spaetere Beobachtungen ergaenzt.
- Platzhalterseiten fuer Beobachtungen, Kompetenzen, Berichte und Einstellungen ergaenzt.
- ViewModels und strukturierte Desktop-App-Unterordner fuer Adapter, Dialoge, Screens und ViewModels eingefuehrt.

### Changed

- Bestehender `StudentDesktopAdapter` in die Adapter-Struktur verschoben und um Gruppenuebersicht sowie Profil-ViewModel erweitert.
- Bestehende Modulnamen bleiben als Kompatibilitaetsimporte erhalten.
- Tests fuer Adapter, ViewModels, Importierbarkeit und fehlende direkte SQLite-Schreiblogik in Widgets erweitert.

### Not Changed

- Keine finale Architekturentscheidung, kein Packaging, keine Beobachtungsmaske, keine Dokumentenverwaltung, kein Excel-Export-Umbau und keine Excel-/VBA-/Builder-Loeschung umgesetzt.

## Spike - PySide6 Desktop-App als alternativer Adapter

### Added

- PySide6 als Spike-Dependency ergaenzt.
- Experimentelle Desktop-App-Struktur unter `src/desktop_app/` angelegt.
- `StudentDesktopAdapter` verbindet die PySide6-nahe Schicht mit `CreateStudentCommand`, `ApplicationCommandDispatcher`, `StudentService` und SQLite-Repositories.
- Tests fuer Command-Erzeugung, Speichern ueber die Application-Schicht und Stammgruppe-/Kurs-Mapping ergaenzt.

### Validated

- PySide6 Desktop-App-Spike manuell validiert: App startet, Maske `Neuer Schüler` funktioniert und ein Schuelerdatensatz wurde in SQLite geschrieben.
- Validierter Pfad: PySide6 GUI -> Desktop Adapter -> ApplicationCommandDispatcher -> StudentService -> SQLiteStudentRepository -> SQLite.
- Tests erfolgreich: `python3 -m pytest` mit 26 bestandenen Tests.
- Build erfolgreich: `python3 build.py`.
- Commit `5363e18` und Tag `spike-pyside6-student-create` sichern den validierten Spike-Stand.

### Removed

- Uncommitted tkinter-Spike-Dateien wieder entfernt, damit nicht zwei GUI-Frameworks parallel im Projekt verbleiben.

### Not Changed

- Keine endgueltige Architekturentscheidung, keine Excel-/VBA-/Seed-Aenderung, keine Builder-Aenderung, kein Projection Refresh, keine Beobachtungen und keine Python-GUI-Zielarchitektur festgelegt.

## Hotfix - Runtime ueber MacScript do shell script starten

### Fixed

- VBA-Prozessstart von `Shell(...)` auf `MacScript("do shell script ...")` umgestellt.
- Die separate Skriptdatei `runtime_python_command.zsh` bleibt der eigentliche Runtime-Command.
- Diagnose protokolliert MacScript-Aufruf sowie Vorhandensein von `runtime_result.json`, stdout, stderr und Exitcode nach dem Start.

### Not Changed

- Keine Aenderungen an Python, `km.py`, SQLite, Dispatcher, StudentService, Repository, Dialoglayout, Named Ranges, Businesslogik oder Projection Refresh umgesetzt.

## Hotfix - Runtime ueber zsh-Skriptdatei starten

### Fixed

- VBA-Runtime-Start auf separate Skriptdatei `runtime_python_command.zsh` umgestellt.
- Verschachtelte `/bin/zsh -lc`-Kette entfernt.
- Diagnose um Skriptpfad und erzeugte Runtime-Artefakte fuer stdout, stderr, Exitcode und Ergebnis erweitert.

### Not Changed

- Keine Aenderungen an Python Command Layer, `km.py`, SQLite, Dispatcher, StudentService, Repository, Dialoglayout, Named Ranges, Projection Refresh oder Businesslogik umgesetzt.

## Hotfix - macOS Python Runtime Start

### Fixed

- VBA-Runtime-Start auf `/bin/zsh -lc` umgestellt, damit Excel fuer macOS Python robuster starten kann.
- Working Directory, stdout-Log, stderr-Log und Exitcode-Datei fuer den Runtime-Aufruf dokumentierbar gemacht.
- Fallback-`runtime_result.json` fuer technische Startfehler im VBA-Startpfad ergaenzt.

### Not Changed

- Keine Aenderungen an Python, SQLite, Dispatcher, StudentService, Repository, Dialoglayout, Named Ranges, Projection Refresh oder Businesslogik umgesetzt.

## Feature 1.4b - Produktiver Speichervorgang bis SQLite

### Added

- `km.py` als produktiven Python Runtime Adapter fuer `student create` ergaenzt.
- `SaveNewStudentDialog()` als VBA Adapter fuer `dlg_neuer_schueler` umgesetzt.
- Runtime-Artefakte `runtime_command.json` und `runtime_result.json` fuer Command- und Ergebnisuebergabe verwendet.
- Unit-Tests fuer den produktiven Runtime-Einstieg bis SQLite ergaenzt.

### Changed

- `ConfigureStudentCardNavigation()` richtet zusaetzlich die Speichern-Aktion der Dialogseite ein.
- Technische Namen, Data Lifecycle, UI Data Mapping, Roadmap, Sprints und Backlog auf den Feature-1.4b-Stand angepasst.

### Not Changed

- Kein Projection Refresh, keine Workbook-Aktualisierung, keine Ruecknavigation zur Stammgruppenuebersicht, keine Dokumente, keine Beobachtungen, keine Kompetenzen und kein Commit umgesetzt.

## Feature 1.4a - Runtime Adapter und Refresh Contract

### Added

- ADR-043 fuer Runtime Adapter und Projection Refresh Contract ergaenzt.
- Produktiven Pfad fuer `student.create` dokumentiert: Dialogseite, VBA Adapter, Python CLI/Bridge, Dispatcher, StudentService, Repository, SQLite.
- Refresh Contract festgelegt: Python erzeugt Projection-Refresh-Paket, VBA importiert ausschliesslich Projection Output.
- Technische Namen fuer vorgesehene Adapter-Prozeduren, CLI/Bridge und Runtime-Artefakte registriert.

### Changed

- Data Lifecycle, Project Constitution, Data Registry, View Ownership, UI Data Mapping, Roadmap, Sprints und Backlog auf den freigegebenen Adapter-/Refresh-Vertrag angepasst.

### Not Changed

- Keine Speicherung, keine Validierung, kein Speichern-Button, kein Python-Aufruf aus VBA, kein SQLite-Schreibprozess aus Excel, kein Workbook-Refresh, keine AppleScript-Tests und kein Commit umgesetzt.

## Hotfix - Dialogseite Eingabeflaechen verbinden

### Fixed

- Eingabefelder auf `dlg_neuer_schueler` als verbundene Eingabeflaechen umgesetzt: `E9:L9`, `E12:L12`, `E15:L15`, `E18:L18` und `E21:L23`.
- Bei verbundenen Eingabefeldern wird die linke obere Zelle entsperrt; die Named Ranges bleiben auf den vollstaendigen Formularbereich ausgerichtet.

### Not Changed

- Keine Speicherung, keine Validierung, kein VBA, kein Python-Command, keine SQLite-Kommunikation, keine AppleScript-Tests und kein Commit umgesetzt.

## Hotfix - Dialogseite editierbar machen

### Fixed

- Blattschutz fuer `dlg_neuer_schueler` korrigiert, damit entsperrte Eingabezellen bei aktivem Schutz ausgewaehlt und beschrieben werden koennen.
- Eingabefelder optisch als weisse Eingabeflaechen mit staerkerem Rahmen hervorgehoben.

### Not Changed

- Keine Speicherung, keine Validierung, kein VBA, kein Python-Command, keine SQLite-Kommunikation, keine AppleScript-Tests und kein Commit umgesetzt.

## Feature 1.3 - Dialogseite fuer Eingabe vorbereiten

### Changed

- Eingabebereiche von `dlg_neuer_schueler` als zentrale registrierte Ranges im Dialogseiten-Builder gefuehrt.
- Nur die Eingabebereiche fuer Vorname, Nachname, Stammgruppe, Kurs und Notiz werden entsperrt; das uebrige Dialogblatt bleibt geschuetzt.
- Abbrechen bleibt als Navigation zur Stammgruppenuebersicht vorbereitet.
- Speichern und `+ Dokument hinzufügen` bleiben optisch vorhanden und weiterhin ohne Funktion.

### Not Changed

- Keine Speicherung, keine Validierung, kein VBA, kein Python-Command, keine SQLite-Kommunikation, keine Dateiauswahl und kein Commit umgesetzt.

## Feature 1 - Architekturwechsel zu worksheet-basierter Dialogseite

### Added

- ADR-042 dokumentiert worksheet-basierte Dialogseiten als primaeres Eingabe-Pattern fuer Excel auf macOS.
- Dialogseite `dlg_neuer_schueler` als geschuetztes Arbeitsblatt mit Feldern, Dokumentbereich sowie Abbrechen-/Speichern-Buttons ergaenzt.
- Absprungpunkt `+ Schüler` auf der Stammgruppenuebersicht zur Dialogseite vorbereitet.
- Technische Namen fuer `dlg_neuer_schueler`, `wsDialogNewStudent` und die Dialog-Anker ergaenzt.

### Changed

- `frm_student_new` als experimenteller/deprecated Artefaktstand eingeordnet.
- Dokumentation von UserForm-zentriertem Feature-1-Pfad auf worksheet-basierte Dialogseiten umgestellt.

### Not Changed

- Keine Speicherlogik, keine Validierung, kein Python-Command, keine SQLite-Kommunikation, kein Dokument-Upload, keine Datei-Auswahl und kein Commit umgesetzt.

## Feature 1.2b - frm_student_new fuer testbare XLSM vorbereiten

### Changed

- Seed-Importprozess erweitert, damit `frm_student_new.frm` zusammen mit den versionierten VBA-Quellen in den Seed importiert werden kann.
- Import- und Packaging-Pruefungen um den von Excel bei echten MSForms-UserForms erzeugten Marker `BaseClass=frm_student_new` erweitert.
- `vba/README.md` um den Form-Import im Seed-Prozess ergaenzt.
- Direkten `.frm`-Import fuer `frm_student_new` ersetzt: Der Seed-Bootstrap erzeugt die Form als echte MSForms-Komponente, damit Designertext nicht als VBA-Code kompiliert wird.
- Programmgesteuerte Form-Erzeugung auf MSForms-Points umgestellt; `.frm`-Twips-Werte werden nun umgerechnet, damit Controls im Designer sichtbar liegen.
- `OpenNewStudentDialog()` als reinen manuellen Anzeigeoeffner ergaenzt, damit `frm_student_new` aus Excel per Makroliste sichtbar geprueft werden kann.
- Anzeigeoeffner fuer die Layoutpruefung vorlaeufig modeless geschaltet, damit Excel bei macOS-Fokusproblemen nicht blockiert.
- Anzeigeoeffner deaktiviert vor dem Anzeigen fehlertolerant Fokusziele der Controls und faengt Anzeige-Fehler ab, damit Excel bei macOS-Fokusproblemen bedienbar bleibt.
- Anzeigeoeffner setzt die UserForm fuer den letzten macOS-Kompatibilitaetstest vor dem Anzeigen explizit auf `500 x 600`.

### Not Changed

- Keine Businesslogik, keine Validierung, keine Adapter-Anbindung, keine Python-Anbindung, keine SQLite-Kommunikation, keine Speicherlogik und keine Event-Prozeduren in der UserForm umgesetzt.

## Feature 1.2 - VBA UserForm nach UX-Prototyp umsetzen

### Changed

- `frm_student_new` rein visuell an das freigegebene UX-Prototyp-Blatt `Feature 1 – Neuer Schüler` angepasst.
- Fensterbreite, Abstaende, Feldgroessen, Notizbereich, Dokumentbereich und Buttonzeile auf das breite Prototyp-Layout ausgerichtet.
- Bestehende registrierte Control-Namen beibehalten.

### Not Changed

- Keine Businesslogik, keine Validierung, keine Pflichtfeldpruefung, keine Events, keine Adapter-Anbindung, keine Python-Aenderung, keine SQLite-Kommunikation, kein Build und kein Commit umgesetzt.

## Dokumentation - UX-Prototyp vor UserForm-Umsetzung

### Added

- UX-Prototyp als verbindlichen Zwischenschritt vor kuenftiger UserForm-Umsetzung dokumentiert.
- Ablauf festgelegt: UX-Prototyp erstellen, UX-Review mit Laura bzw. Product Owner, UX-Freigabe, danach VBA-UserForm moeglichst 1:1 umsetzen, Validierung/Adapter/Logik erst danach.
- ADR-041 fuer den UX-Prototyp als verbindliche UserForm-Referenz ergaenzt.
- Feature-1-Prototyp `output/Jenaplan_UX_Prototype_v0.1.xlsx` mit Blatt `Feature 1 – Neuer Schüler` als visuelle Vorlage fuer `frm_student_new` dokumentiert.

### Not Changed

- Keine Implementierung, keine Python-Aenderung, keine VBA-Aenderung, keine UserForm-Aenderung, kein Build und kein Commit umgesetzt.

## Feature 1.1 - UserForm Neuer Schueler fertigstellen

### Changed

- Dokumentbereich der UserForm `frm_student_new` als sichtbaren Bestandteil des Referenzdialogs bestaetigt.
- Empty-State-Text des Dokumentbereichs auf `Noch keine Dokumente vorhanden.` vereinheitlicht.

### Not Changed

- Keine Speicherlogik, keine Validierung, keine Pflichtfeldpruefung, keine Python-Anbindung, keine Dispatcher-Anbindung, keine SQLite-Kommunikation, keine Excel-Automation, kein Datei-Upload, keine Dateiauswahl und kein Build umgesetzt.

## Architecture Baseline v2.0

### Added

- ADR-040 `Architecture Baseline v2.0` mit Status `Accepted` ergaenzt.
- Aktuelle Schichtenarchitektur dokumentiert: Adapter Layer, Application Layer, Domain Layer, Infrastructure Layer, Projection Layer und Excel UI.
- Architecture v1 historisch als `Python -> Workbook Builder -> Excel` eingeordnet.
- Standard-Datenfluss fuer zukuenftige Schreibprozesse dokumentiert.

### Not Changed

- Keine Implementierung, keine Python-Aenderung, keine VBA-Aenderung, kein Build, keine Tests und keine Excel-Automation umgesetzt.

## Sprint 5.4 - student.create End-to-End ohne Adapter

### Added

- `student.create` End-to-End durch Application Dispatcher, `StudentService`, `SQLiteStudentRepository` und SQLite getestet.
- `SuccessResult` und `ErrorResult` als Command-Ergebnisse ergaenzt.
- `SQLiteStudentRepository` um schreibende Student-Operationen erweitert.
- Unit-Tests fuer erfolgreichen SQLite-Schreibpfad und Fehlerfaelle ergaenzt.

### Not Changed

- Keine CLI, keine VBA-Anbindung, keine UserForm-Anbindung, keine Excel-Automation, kein Build, keine Beobachtungen, keine Dokumente, keine Kompetenzen und keine Berichte umgesetzt.

## Sprint 5.3 - Application Command Layer Architecture Spike

### Added

- Application Command Layer als neue Architekturschicht zwischen Command-Adaptern und Domain Services eingefuehrt.
- `ApplicationCommandDispatcher` als nicht-produktiven Dispatcher-Prototyp ergaenzt.
- `CreateStudentCommand` als erstes Command-DTO fuer `student.create` ergaenzt.
- Reservierte Command-Namespaces fuer `observation` und `report` angelegt.
- Tests fuer Dispatcher-Registrierung und Delegation an einen Student-Service-Handler ergaenzt.
- ADR-038 fuer Application Command Layer, CLI als Adapter und spaetere VBA-Anbindung dokumentiert.

### Not Changed

- Keine produktive CLI, keine UserForm-Anbindung, keine VBA-Aenderung, keine Beobachtungs-, Dokument- oder Report-Funktion, keine Build-Aenderung und keine Excel-Automation umgesetzt.

## Sprint 5.2a - SQLite Architecture Spike

### Added

- SQLite-Spike-Datenbank unter `data/kompetenzmanager.sqlite` erzeugt.
- Initiales SQLite-Schema fuer `students`, `groups` und `courses` prototypisiert.
- `SQLiteDatabase`, `SQLiteStudentRepository`, `SQLiteGroupRepository` und `SQLiteCourseRepository` als Spike-Komponenten ergaenzt.
- Spike-Skript `scripts/create_sqlite_spike.py` ergaenzt, das Seed-Daten nach SQLite schreibt und eine separate Excel-Projektion aus SQLite-Daten erzeugt.
- Unit-Tests fuer Seed-Migration, Repository-Lesen und Builder-Projektion aus SQLite ergaenzt.
- ADR-037 fuer SQLite als gepruefte Zielarchitektur ergaenzt.

### Changed

- Dokumentation um SQLite als moegliche zentrale Datenbasis erweitert.
- `data/` als bestehende Projektkonvention fuer die Spike-Datenbank dokumentiert; der vorgeschlagene Pfad `Daten/kompetenzmanager.sqlite` wird deshalb nicht neu eingefuehrt.

### Not Changed

- Keine vollstaendige Migration, keine produktive UserForm-Anbindung, keine VBA-zu-Python-Bridge, keine direkte VBA-SQLite-Anbindung, kein Seed-Import und keine Aenderung am produktiven Buildpfad umgesetzt.

## Sprint 5.1b - Technischer Stopp der produktiven Schueleranlage

### Added

- ADR-036 dokumentiert den fehlenden freigegebenen Laufzeitpfad von VBA-UserForm zu Python-`StudentService`.
- Technische Optionen fuer die Schueleranlage ueber UserForm dokumentiert: Python Build/Import Workflow, VBA Repository-Schicht, CSV/Hidden-Sheet Command Queue und spaeter SQLite/API.
- Empfehlung fuer einen naechsten Architekturspike zur Command-Queue-Variante dokumentiert.

### Not Changed

- `frm_student_new` wurde nicht produktiv angebunden.
- Keine Speicherlogik, keine StudentService-Anbindung, kein direkter Tabellenzugriff, kein Seed-Import, keine Excel-Automation und kein Build umgesetzt.

## Sprint 5.1a - Dialog Framework vorbereiten

### Added

- Dialogstandard fuer modale VBA-UserForms in `docs/DESIGN_SYSTEM.md` konkretisiert.
- `frm_student_new` als nicht-produktive Referenzimplementierung des Dialog Frameworks beschrieben.
- Vorgesehenen Dialogoeffner `OpenNewStudentDialog()` in der Technical Naming Registry ergaenzt.

### Changed

- `frm_student_new.frm` minimal an den Dialogstandard angepasst: Enter loest Speichern aus, Esc loest Abbrechen aus.

### Not Changed

- Keine produktive Schueler-Speicherlogik, keine Datenänderung, keine StudentService-Anbindung, kein Tabellenzugriff, kein Build, keine Excel-Automation und kein Import in den Seed umgesetzt.

## Sprint 5 - Dialog Framework, Schuelerverwaltung und Dokumentenarchitektur

### Status

- Scope Freeze abgeschlossen.
- Dialog Framework begonnen.
- Erste UserForm `frm_student_new` vorbereitet.
- Schuelerverwaltung begonnen, aber noch nicht produktiv freigegeben.

### Added

- Standard fuer modale VBA-UserForms dokumentiert.
- `frm_student_new` als erste Referenzimplementierung des Dialog Frameworks fuer den Dialog `Neuer Schueler` eingeordnet.
- Benannte Label-, Eingabe-, Auswahl-, Dokument- und Button-Controls fuer den Referenzdialog in der Technical Naming Registry ergaenzt.
- Studentenzentrierte Dokumentenstruktur mit `Dokumente/<student_id>/Hauptdokumente/` und `Dokumente/<student_id>/Beobachtungsanhaenge/<observation_id>/` dokumentiert.
- Beobachtungsdialog als spaeterer Zielzustand mit Kompetenzen, Bewertung, Notiz sowie Dokumenten und Medien vorbereitet.
- Schnellbeobachtung / Gruppenbewertung als Backlog-Thema ergaenzt.
- ADR-035 fuer modale UserForms und studentenzentrierte Dokumentreferenzen ergaenzt.

### Changed

- Sprint-Dokumentation auf den freigegebenen Projektstand ausgerichtet: Sprint 5 ist nicht mehr reine Planung, sondern begonnen.
- `data_media` in der Workbook Data Registry von rein beobachtungsbezogenen Anlagen zu studentenzentrierten Dokument- und Medienreferenzen erweitert.
- Data Lifecycle, View Data Ownership und UI Data Mapping um Schuelerdokumente, Beobachtungsanhaenge und den Neuer-Schueler-Dialog ergaenzt.
- Technical Naming Registry um UserForm- und Control-Namen sowie Dokument-/Medienfelder erweitert.

### Not Changed

- Keine Speicherlogik, keine Tabellenzugriffe, keine Service- oder Repository-Aufrufe, keine Dokumentauswahl, keine VBA-Navigation und keine Build-Anpassung umgesetzt.
- Keine produktive Freigabe der UserForm, keine Beobachtungserfassung, keine Schnellbeobachtung, kein vollstaendiges Dokumentenmanagement und keine Datei-Vorschau umgesetzt.

## VBA-Seed-Import-Automation

### Added

- `vba/modules/SeedImport.bas` als dauerhaftes Bootstrap-Makro fuer den Seed ergänzt.
- `scripts/import_vba_sources_to_seed.py` und `scripts/import_vba_sources_to_seed.applescript` zum automatischen Aktualisieren der versionierten VBA-Module im Seed ergänzt.

### Changed

- `vba/README.md` um den automatischen Seed-Import-Workflow und die Bootstrap-Grenze erweitert.
- `SeedImport` meldet blockierten Zugriff auf `ThisWorkbook.VBProject` mit einer expliziten Ursache statt eines rohen Excel-Fehlers 1004.

### Not Changed

- Keine fachliche Logik, keine Workbook-Datenquellen, keine UI-Projektionen und keine Designregeln geaendert.

## UX-Verbesserung - temporaeren UI-State zuruecksetzen

### Added

- Architekturregel fuer temporaeren UI-State in `VIEW_DATA_OWNERSHIP.md` ergänzt.
- VBA-Navigation `OpenClassOverview` ergänzt, die den Suchzustand der Stammgruppenuebersicht vor dem Ruecksprung leert.
- Technischer Anker `ui_profile_back_to_class_overview` fuer den Ruecksprung aus dem Schuelerprofil ergänzt.

### Changed

- `ConfigureStudentCardNavigation` konfiguriert zusaetzlich die klickbare Ruecksprungflaeche im Schuelerprofil.
- `OpenClassOverview` leert das Suchfeld merge-sicher ueber den gesamten Eingabebereich.

### Not Changed

- Keine fachlichen Daten, keine Student-Entity-Schichten und keine Datenquellen geaendert.

## Sprint 4.2c

### Added

- `StudentValidator`, `StudentRepository`, `StudentService` und `StudentProjectionBuilder` als Referenzimplementierung fuer die Entity Student ergänzt.
- Unit-Tests fuer create, update, archive, ID-Kollision und Workbook-Projektion ergänzt.

### Changed

- Seed-IDs kontrolliert von `s001` auf `STU-000001`-Format migriert.
- Gruppen- und Kurs-Seed-IDs auf `GRP-000001` und `CRS-000001`-Format umgestellt.
- `tbl_students` um `student_notes` und `archived_at` erweitert.
- Student-Projektionen verwenden technische Feldnamen aus `src/core/constants.py`.
- Legacy-Named-Range `ui_profile_student_s001` entfernt, da sie nicht als zentraler Navigationsanker verwendet wird.

### Not Changed

- Keine Excel-Verwaltungsansicht, keine Testmaske, keine VBA-Architekturänderung, kein `GroupRepository` und kein `CourseRepository` eingefuehrt.

## Sprint 4.2b Architecture Gate

### Changed

- Builder-Regel praezisiert: Builder veraendert keine fachlichen Entitaeten und erzeugt ausschliesslich Workbook-Struktur und Projektionen.
- Fuer Schuelerprojektionen `tbl_students`, `tbl_groups` und `tbl_courses` als lesende Quellen bestaetigt.
- Festgelegt, dass Sprint 4.2 keine neue Verwaltungsansicht und keine Testmaske erstellt.
- Validator-Kontext fuer `StudentValidator` dokumentiert: gueltige `group_id` und `course_id` kommen aus dem `StudentService`-Kontext.
- Legacy-Analyse fuer Student-ID-Referenzen dokumentiert.

### Not Changed

- Keine Implementierung, keine Tests, kein Build, keine VBA-Aenderung und keine Migration umgesetzt.

## Sprint 4.2a

### Added

- Student-Blueprint als Referenzarchitektur fuer die erste fachliche Verwaltungs-Entity dokumentiert.
- Verbindliche projektweite ID-Strategie mit `STU-000001`, `GRP-000001`, `CRS-000001`, `CMP-000001`, `OBS-000001` und `MED-000001` ergänzt.
- Zentrale technische Konstantendatei `src/core/constants.py` angelegt.
- ID-Migrationsplan fuer die spaetere Umstellung der Seed-IDs auf `STU-000001` dokumentiert.

### Changed

- Student-Felder in der Workbook Data Registry um `student_notes` und `archived_at` erweitert.
- Archivierung im Data Lifecycle konkretisiert: `active = FALSE`, `archived_at` als Zeitstempel, historische Daten bleiben erhalten.
- Project Constitution um den Entity-Aufbau `Entity -> Validator -> Repository -> Service -> Builder -> UI -> Navigation` ergänzt.

### Not Changed

- Keine Benutzerfunktion, kein Validator, kein Repository, kein Service, keine Schreiblogik, keine UI-Anpassung, keine VBA-Aenderung und kein Build umgesetzt.

## v0.4 - Core Data Architecture + datengetriebene Workbook-Projektion

### Added

- Core Data Architecture abgeschlossen und erstmals vollständig durch den Build validiert.
- Workbook Data Builder erzeugt `data_students`, `data_groups` und `data_courses` als versteckte Tabellenblaetter mit `tbl_students`, `tbl_groups` und `tbl_courses`.
- Workbook Data Registry in der physischen Workbook-Struktur umgesetzt.

### Changed

- Stammgruppenuebersicht und Schuelerprofil lesen die Beispieldaten aus den Workbook-Datenquellen statt aus direkt im UI definierten Schuelerdaten.
- Builder erzeugt UI-Projektionen aus den registrierten Datenquellen.
- Stammgruppenuebersicht liest Schueler aus `tbl_students`.
- Schuelerprofil liest den Profilkopf ueber `student_id` aus `tbl_students`.
- Workbook Data Registry und UI Data Mapping auf die Phase-1-Felder `active`, `group_name`, `course_name` und `color_key` geschärft.
- Build-Ausgabe auf `output/Jenaplan_Kompetenzmanager_v0.4.xlsm` vereinheitlicht.
- VBA-Navigation bleibt weiterhin funktionsfähig.

### Fixed

- Die Sortierung der Stammgruppenuebersicht erfolgt wieder vollstaendig im Python Projection Builder.
- Excel-SORTBY wurde entfernt, um eine stabile Zuordnung zwischen Schuelerkarte, `student_id` und VBA-Navigation sicherzustellen.

### Improved

- Stammgruppenuebersicht sortiert Schueler nach Kurs und anschliessend alphabetisch.
- Sortierung erfolgt ausschliesslich innerhalb der UI-Projektion.

### Known Open Points

- Seed enthält aktuell 28 Testschueler; Demo-Seed und Minimal-Seed werden spaeter getrennt.
- Kursfarben werden noch nicht dynamisch aus `tbl_courses[color_key]` im Workbook projiziert.
- Header `Stammgruppenübersicht` wird in der aktuellen Darstellung noch abgeschnitten.

### Not Changed

- Keine Verwaltungsfunktion, keine Dialoge, keine VBA-Erweiterung, keine Kursuebersicht und keine Beobachtungserfassung implementiert.

## Sprint 4.0c

### Added

- Entity-first-Prinzip, Entity/Storage/Projection-Trennung und Builder-Schicht als verbindliche Architekturprinzipien ergänzt.
- Transaktionales Denken fuer Schreibprozesse dokumentiert.
- Owner je zentraler Datenquelle in der Workbook Data Registry ergänzt.
- Änderungs-Lifecycles fuer Schueler, Stammgruppe, Kurs und Kompetenz ergänzt.
- ADR-032 Entity-first-Architektur, ADR-033 Builder-Schicht und ADR-034 offene Historisierung von Bezeichnern ergänzt.
- Backlog-relevante Architekturanforderungen ohne Feature-Spezifikation aufgenommen.

### Changed

- View Ownership fachlich begrenzt: Ansichten duerfen nur fachlich begruendete Datenquellen lesen.
- Codex-Regeln um Dokumentationsbegrenzung ab Sprint 4.1 erweitert.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Excel-Datei, kein Build und keine Produktfunktion geaendert.

## Sprint 4.0b

### Added

- ADR-031 `Dokumentation geht Implementierung voraus` ergänzt.
- Verbindliche Implementierungsreihenfolge fuer neue Funktionen dokumentiert.

### Changed

- Technische Namenskonvention finalisiert: technische Namen sind englisch, ASCII-kompatibel und stabil; sichtbare Begriffe duerfen sich aendern.
- Physische Workbook-Datenbank finalisiert: `data_*`-Quellen werden als versteckte Tabellenblaetter mit `tbl_*`-Tabellen angelegt.
- Legacy-Regeln fuer bestehende technische Namen wie `wsClassOverview` und `ui_class_search` dokumentiert.
- View Ownership um die Regel erweitert, dass Ansichten nur dokumentierte Datenquellen verwenden duerfen.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Workbook-Artefakte, kein Build und keine Produktfunktion geaendert.

## Sprint 4.0a

### Added

- View Data Ownership fuer Ansichten, erlaubte Datenquellen, Schreibrechte, IDs und UI-Projektionen erstellt.
- Data Lifecycle fuer zentrale Schreibprozesse wie Schueleranlage, Archivierung, Beobachtungserfassung, Kompetenzergänzung und Medienanlage erstellt.

### Changed

- Project Constitution um Identitaets-, Projektions-, Erweiterbarkeits- und Schattenlogik-Regeln vertieft.
- Workbook Data Registry um Foreign Keys, Schreib-/Leseprozesse, erlaubte UI-Projektionen und Erweiterungsregeln je Datenquelle vertieft.
- UI Data Mapping um Projektionstyp, Schreibregel und verantwortliche Datenquelle erweitert.
- Codex-Arbeitsregeln in `AGENTS.md` um View Ownership und Data Lifecycle erweitert.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Excel-Datei, kein Build und keine Produktfunktion geaendert.

## Sprint 4.0

### Added

- Projektverfassung fuer Source-of-Truth-Regeln und Architekturprinzipien erstellt.
- Technical Naming Registry fuer technische Namen, Praefixe, IDs, Named Ranges und Shape-Muster erstellt.
- Workbook Data Registry fuer zentrale Datenquellen erstellt.
- UI Data Mapping fuer die Herkunft sichtbarer UI-Informationen erstellt.

### Changed

- VBA-Dokumentation um den Standard fuer spaetere Absprungpunkte ergaenzt.
- Codex-Arbeitsregeln in `AGENTS.md` um Registry-Pruefungen vor Codeaenderungen ergaenzt.

### Not Changed

- Keine Python-Dateien, keine VBA-Quellen, keine Excel-Datei und keine Produktfunktion geaendert.

## Sprint 3.5g

### Changed

- Initialisierungsabhängigkeit in `OpenStudentProfileById` beseitigt: Das Zielblatt wird aus dem technischen Profil-Named-Range abgeleitet und vor der Nutzung geprüft.
- Named-Range-Zugriffe in `Navigation.bas` und `UI.bas` ohne `On Error Resume Next` auf explizite Workbook-Namenssuche umgestellt.

### Not Changed

- Keine Doppelaufrufe, keine `Workbook_Open`-Logik, keine Designänderung und keine Fachlogik umgesetzt.

## Sprint 3.5f

### Changed

- Sichtbare Bezeichnung der bisherigen Übersicht auf `Stammgruppenübersicht` finalisiert.
- Schülerkarten zeigen in der Stammgruppenübersicht den Kurs statt der Stammgruppe.
- Kartenfarben der Schülerkarten werden aus der Kurszuordnung abgeleitet vorbereitet.
- UX-Dokumentation zur sichtbaren Terminologie, Kursanzeige und kursbasierten Kartenfarbe aktualisiert.

### Not Changed

- Keine neue Ansicht, keine neue Fachfunktion, keine Designänderung, keine VBA-Navigation und keine technischen Navigationsnamen geändert.

## Sprint 3.5e

### Changed

- `ConfigureStudentCardNavigation` für den Erstaufruf stabilisiert: numerische Office-Ersatzkonstanten zentralisiert und technische Anker defensiv geprüft.
- Die Klassenübersicht für die Shape-Erzeugung wird aus dem technischen Pfeil-Anker ermittelt, ohne sichtbare Blattnamen zu verwenden.

### Not Changed

- Kein `Auto_Open`, keine AppleScript-Automation, keine Designänderung und keine Fachlogik umgesetzt.

## Sprint 3.5d

### Changed

- Klickfläche der VBA-Schülerkartennavigation auf den sichtbaren Pfeil der jeweiligen Karte begrenzt und nach vorn gelegt.
- Temporäre Diagnose für Schülerkarten-Navigation ergänzt: geklicktes Shape, erkannter Slot und gelesene `student_id` werden beim Test angezeigt.

### Not Changed

- Keine Designänderung, keine Suche-Änderung, kein `Auto_Open`, keine Beobachtungslogik und keine neue Fachfunktion umgesetzt.

## Sprint 3.5c

### Changed

- `UI.bas` compile-sicher für Excel macOS bereinigt: Excel-Objekte werden spät gebunden, problematische Variablennamen vermieden und Office-Konstanten durch kommentierte numerische Werte ersetzt.

### Not Changed

- Keine Import-Automation, kein `Auto_Open`, keine Designänderung, keine Fachlogik und keine Beobachtungslogik umgesetzt.

## Sprint 3.5b

### Changed

- VBA-Variablennamen in der Karten-Navigation compile-freundlich bereinigt und Kollisionen mit Excel-Objekttypen vermieden.

## Sprint 3.5a

### Changed

- VBA-Navigation nutzt technische Sheet-CodeNames statt sichtbarer Blattnamen mit Umlauten.
- Defensive Meldungen ergänzt, wenn keine `student_id` gelesen werden kann oder der technische Profil-Zielbereich fehlt.

## Sprint 3.5

### Added

- VBA-Navigation für Schülerkarten vorbereitet: sichtbare Karten-Slots erhalten versteckte `student_id`-Projektionen und werden über zentrale VBA-Logik geöffnet.
- Schülerprofil erhält eine definierte technische Zielzelle für die aktuell übergebene `student_id`.

### Changed

- Direkter Hyperlink-Testpfad von der Schülerkarte zum Schülerprofil wurde durch VBA-Navigation ersetzt.
- Versionierte VBA-Quellen `Globals`, `Navigation` und `UI` um zentrale Karten-Navigation erweitert.

### Not Changed

- Keine Beobachtungslogik, keine UserForms, keine Kursübersicht und keine Designänderungen umgesetzt.

### Technical Notes

- Der `.xlsm`-Seed muss nach VBA-Quelländerungen in Excel aktualisiert werden; ein automatischer Import der geänderten `.bas`-Quellen in `vbaProject.bin` konnte in dieser Umgebung nicht validiert werden.

## Sprint 3.4

### Added

- Design-System als verbindliche Referenz für alle zukünftigen Ansichten dokumentiert.
- Stammgruppe und Kurs als eigenständige fachliche Entitäten dokumentiert.
- Kursübersicht als zukünftige Hauptansicht aufgenommen.
- Backlog um Schülerverwaltung, Stammgruppenverwaltung, Kursverwaltung und Kursübersicht erweitert.

### Changed

- Domänensprache von Klasse auf Stammgruppe präzisiert.
- Bisherige Klassenübersicht künftig als Stammgruppenübersicht dokumentiert.
- Datenmodell-Dokumentation um `stammgruppe_id` und `kurs_id` für Schüler erweitert.

### Not Changed

- Kein Code, keine VBA-Dateien, kein Seed und kein Build wurden in Sprint 3.4 geändert.

## Sprint 3.3f

### Changed

- Klassenübersicht öffnet im UX-Prototyp wieder mit 140 % Zoom gemäß freigegebener Design-Referenz.

## Sprint 3.3d

### Changed

- VBA-Seed-Bereinigung geprüft und dokumentiert.
- Packaging-Skript gegen alte Seed-Strukturen abgesichert: `Globals`, `Navigation` und `UI` müssen im Seed vorhanden sein; `Modul1` darf nicht mehr registriert sein.
- Workbook- und Worksheet-CodeNames werden im PoC soweit technisch möglich über `openpyxl` gesetzt.
- `seeds/JenaplanSeed.xlsm` als bereinigte Modulbasis validiert: `Globals`, `Navigation` und `UI` sind registriert; `Modul1` ist nicht mehr als Modul registriert.
- Zielarbeitsmappe `Jenaplan_UX_Prototype_v0.3_VBA_Framework.xlsm` erfolgreich mit `xl/vbaProject.bin`, `Klassenübersicht` und `Schülerprofil` erzeugt.

### Technical Notes

- Excel-Objekte des Seeds bleiben auf die Seed-Arbeitsmappe beschränkt.
- Die fachlich relevanten Excel-Objekte entstehen in der generierten Framework-Datei und werden dort als `DieseArbeitsmappe`, `wsClassOverview` und `wsStudentProfile` gesetzt.
- Alte Textfragmente können im binären `vbaProject.bin` noch per `strings` sichtbar sein; maßgeblich ist die registrierte `Module=`-Struktur.

## Sprint 3.3c

### Added

- VBA-Seed-Validierung dokumentiert: Python kann eine `.xlsm` mit `keep_vba=True` laden, verändern und speichern, ohne `xl/vbaProject.bin` zu verlieren.
- `.xlsm` als künftiges Zielartefakt vorbereitet; `.xlsx` bleibt Fallback, bis das VBA-Framework stabil ist.
- Versionierbare VBA-Quellstruktur unter `vba/` ergänzt.
- Erste VBA-Quellmodule angelegt: `Globals.bas`, `Navigation.bas`, `UI.bas`.
- Separaten PoC-Packaging-Schritt für `Jenaplan_UX_Prototype_v0.3_VBA_Framework.xlsm` ergänzt.

### Not Changed

- Keine Produktlogik, keine Fachlogik und keine UserForms umgesetzt.
- `build.py`, `src/` und bestehende UX-Screens nicht geändert.
- Die neuen `.bas`-Quellen sind noch nicht in das binäre `vbaProject.bin` importiert; der PoC erhält zunächst das validierte Seed-VBA-Projekt.

## Sprint 3.3a

### Changed

- Zielplattform dauerhaft auf Microsoft Excel für macOS festgelegt.
- Konsolidierte Zielarchitektur dokumentiert: Python für Build-System, Workbook-Erzeugung, Datenmodell, UI-Projektionen, Styles, Berichte und Fachlogik; VBA nach erfolgreichem Packaging ausschließlich für Interaktion.
- Standard-Reihenfolge jeder Implementierung dokumentiert.
- Datenmodell als zentrale fachliche Grundlage hervorgehoben.
- Projektdokumentation bereinigt und Roadmap auf den aktuellen UX-Prototyp-Pfad ausgerichtet.

### Not Changed

- Keine funktionalen Änderungen.
- Kein Python, keine Excel-Dateien und keine VBA-Implementierung geändert.

## Technischer Spike VBA-Packaging

### Added

- ADR-027 um das Packaging-Ergebnis ergänzt: Ein `.xlsm`-PoC ist ohne echtes `vbaProject.bin` oder validierte `.xlsm`-Seed-Datei nicht aussagekräftig.
- Dokumentiert, dass `openpyxl` vorhandene VBA-Projekte mit `keep_vba=True` erhalten kann, aber kein neues VBA-Projekt erzeugt.
- Künftigen Build-Prozess dokumentiert: Python erzeugt Workbook, Datenmodell, UI-Projektionen und Styles; der Packaging-Schritt übernimmt ein validiertes VBA-Projekt ausschließlich als Interaktionsschicht.

### Not Created

- Kein `.xlsm`-PoC erzeugt, da im Repository aktuell kein `vbaProject.bin`, keine `.xlsm`-Vorlage und kein exportiertes VBA-Projekt vorhanden ist.

## ADR-Spike VBA

### Added

- ADR-027 zur Einführung von VBA als Interaktionsschicht ergänzt.
- Variantenbewertung `.xlsx` mit Formeln gegenüber `.xlsm` mit VBA dokumentiert.
- Empfehlung dokumentiert: Python bleibt für Workbook, Datenmodell, UI-Projektionen, Styles und Build-Artefakte verantwortlich; VBA übernimmt ausschließlich Interaktion.
- Technisches Spike-Ergebnis dokumentiert: lokales Excel ist erreichbar, automatisierte `.xlsm`-Erzeugung mit eingebettetem VBA ist ohne `vbaProject.bin` oder freigegebene VBA-Projekt-Injektion noch nicht validiert.

## Sprint 3.2

### Added

- Schülerprofil als zweiter UX-Screen in `Jenaplan_UX_Prototype_v0.2.xlsx` ergänzt.
- Klickbarer Testpfad von der Klassenübersicht zum Schülerprofil für `student_id s001` umgesetzt.
- Beispielhafte Beobachtungskarten im Schülerprofil ergänzt.
- Zurück-Link vom Schülerprofil zur Klassenübersicht ergänzt.

### Deferred

- Zentraler Beobachtungsdialog bleibt zurückgestellt.
- Dynamische Navigation für alle Schüler bleibt zurückgestellt; Sprint 3.2 bindet den Testpfad bewusst über `student_id s001` an.

## Sprint 3.1f

### Added

- Produktentscheidung dokumentiert: `Neue Beobachtung` darf als Schnellzugriff aus der Klassenübersicht und als Aktion im Schülerprofil erreichbar sein.
- Architekturentscheidung dokumentiert: Beide Einstiege öffnen denselben zentralen Beobachtungsdialog.
- Dokumentiert, dass die Klassenübersicht ausschließlich `student_id` an den Beobachtungsdialog übergibt und keine eigene Beobachtungslogik enthält.

## Sprint 3.1e

### Changed

- Verbindung zwischen verborgener UI-Projektion und sichtbaren Schülerkarten repariert.
- Live-Suche auf einfache Treffer-Hilfsspalten und `INDEX`/`MATCH` umgestellt.
- Suche auf den Vornamen ausgerichtet, passend zur Standardsortierung der Klassenübersicht.
- Leerer Suchzustand zeigt wieder alle 28 aktiven Schüler.
- Kein-Treffer-Zustand zeigt `Kein Schüler gefunden`.

## Sprint 3.1d

### Added

- Datenmodell-Schutz für die Klassenübersicht dokumentiert.
- Verborgene UI-Projektion der Klassenübersicht um `student_id`, `first_name`, `last_name`, `display_name`, `class_id`, `status` und `search_key` abgesichert.
- ID-basierte UI-Anker für Schülerkarten ergänzt.

### Changed

- Schülernamen werden nicht mehr als technische Identität verwendet.
- Sichtbare Karten und Live-Suche leiten sich ausschließlich aus der verborgenen UI-Projektion ab.

## Sprint 3.1c

### Added

- Live-Suche in der Klassenübersicht ergänzt.
- Suchfeld filtert die Schülerkarten automatisch ohne Suchbutton.
- Sortierung nach Vorname technisch über die alphabetisch sortierte Schülerdatenquelle der Klassenübersicht umgesetzt.

### Changed

- Klassenübersicht bleibt optisch im v0.2-Referenzdesign; ergänzt wurde ausschließlich die Suchfunktion.

## Sprint 3.1b

### Added

- Produktentscheidung dokumentiert: Die Klassenübersicht ist ausschließlich Einstieg, Such- und Auswahlansicht.
- Produktentscheidung dokumentiert: Jede Ansicht besitzt genau eine Hauptaufgabe.
- Projektstandard dokumentiert: Schüler werden in der Klassenübersicht alphabetisch nach Vorname sortiert.
- Produktentscheidung dokumentiert: Schülerverwaltung erfolgt künftig in einer separaten Klassenverwaltung.
- Architekturprinzip dokumentiert: Die Klassenübersicht besitzt keine eigene Geschäftslogik und wird aus vorhandenen Schülerdaten generiert.
- Design Freeze für das aktuelle Referenzdesign der Klassenübersicht dokumentiert.

### Changed

- UX Blueprint zur Klassenübersicht an die Sprint-3.1/3.1a-Entscheidungen angepasst.

## Sprint 3.1a

### Added

- UX-Review der Klassenübersicht dokumentiert und in Layoutentscheidungen übertragen.
- `src/ui/theme.py` und `src/ui/components.py` als wiederverwendbare UI-Basis für Excel-Screens ergänzt.
- Dynamische UI-Anker für 28 Schülerkarten vorbereitet.

### Changed

- Klassenübersicht auf bis zu 28 Schüler optimiert.
- Schülerkarten deutlich kompakter gestaltet.
- Der separate Button `Schülerprofil` wurde entfernt; die gesamte Karte ist als spätere Klickfläche vorbereitet.
- Suchfeld auf eine kompakte, einzeilige Fläche reduziert.
- Raster auf eine 4-spaltige, unterrichtstaugliche Übersicht umgestellt.
- Screen-Code aus `src/ui/screens/klassenuebersicht.py` in Theme, Komponenten und Screen-Verantwortung getrennt.

### Deferred

- Sichtbarkeit und Platzierung von `Neue Beobachtung` blieben bis zur Produktentscheidung in Sprint 3.1f offen.
- Echte Navigation, VBA-Code und UserForms bleiben zurückgestellt.
- Schülerprofil, Beobachtungsdialog, Kompetenzansicht und fachliche Auswertungen bleiben unverändert außerhalb dieses Sprints.

## Sprint 3.1

### Added

- Klassenübersicht für `Jenaplan_UX_Prototype_v0.2.xlsx` als einzige v0.2-Ansicht umgesetzt.
- Hochwertiges Excel/macOS-Layout mit ausgeblendeten Gitternetzlinien, ausgeblendeten Zeilen- und Spaltenköpfen sowie ausgeblendeten Blattregistern erstellt.
- Stabile benannte UI-Anker für spätere VBA-Interaktion ergänzt.

### Changed

- v0.2-Build erzeugt keine Schülerprofil-, Beobachtungs-, Kompetenz- oder Dashboard-Blätter mehr.
- Projektstatus und Sprintplanung auf Sprint 3.1 aktualisiert.

## Sprint 3.0

### Added

- ADR-021 zur UI-Technologie ab UX-Prototyp v0.2 ergänzt.
- Vorbereitende Projektstruktur für `src/core/`, `src/ui/`, `src/ui/screens/` und `vba/` angelegt.
- Build-Ziele für `Jenaplan_UX_Prototype_v0.1_FirstAttempt.xlsx` und `Jenaplan_UX_Prototype_v0.2.xlsx` vorbereitet.

### Changed

- Zielplattform auf Microsoft Excel für macOS umgestellt.
- Projektregeln und Dokumentation auf Python-Generator plus UI-VBA ohne fachliche Logik aktualisiert.
- Bestehender UX-Prototyp v0.1 wird beim Build als First Attempt erhalten.

## Sprint 2c

### Added

- Erster klickbarer UX-Prototyp auf Basis des UX Blueprint v1.0 erstellt.
- Prototyp-Versionierung auf `UX Prototype v0.1` umgestellt.
- Klassenübersicht, Schülerprofil, Neue Beobachtung und Kompetenzansicht als prototypische Excel-Bildschirme umgesetzt.

## Sprint 2b

### Added

- ADR-012 als UX- und Architekturentscheidung zu Single Purpose Views dokumentiert.
- UX_BLUEPRINT.md v1.0 als Grundlage für den ersten Excel-Prototyp erstellt.

## Sprint 2a

### Added

- Discovery Phase 1 dokumentiert.
- DISCOVERY.md eingeführt.
- Fachliche Erkenntnisse aus Anwenderinterviews dokumentiert.
- Unterrichtskontexte beschrieben.
- Kompetenzentwicklung präzisiert.

## Projektinfrastruktur

### Added

- Product Backlog eingeführt.
- BACKLOG.md als Bestandteil der Projektstruktur ergänzt.

## Sprint 1.2

### Added

- Fachliches Domänenmodell dokumentiert.
- Lernentwicklungsmanager als Produktvision definiert.
- Beobachtungen als Source of Truth festgelegt.
- Historisierung der Kompetenzentwicklung dokumentiert.
- Discovery-Erkenntnisse aus erster Lehreranalyse übernommen.

## Version 3.2

### Added

- Pädagogische Produktvision dokumentiert
- Fachliche Leitlinien ergänzt
- Produktentscheidungen erweitert
- Roadmap um langfristige Produktziele ergänzt
- VISION.md ergänzt

### Changed

- Ersten Excel-Generator implementiert
- WorkbookBuilder für Arbeitsmappenerzeugung erstellt
- Blattmodule für Dashboard, Schüler, Kompetenzen, Bewertungen, Einstellungen und Changelog umgesetzt
- Zentrale Stylestruktur für Arbeitsmappen und Tabellen eingeführt
- Build-Prozess für output/Jenaplan_v3.2.xlsx eingerichtet
- Sprintplanung und Projektdokumentation auf Sprint 1 aktualisiert

## Version 3.1

- Datenmodell erstellt
- Projektgenerator eingerichtet
- Projektdokumentation erstellt
- Architekturentscheidungen dokumentiert
- README und Projektregeln aktualisiert

## Brand Color Harmonization

### Changed

- Zentrale Brand-Navy-, Blue-, Teal-, Green-, Lime- und Orange-Rollen samt
  heller Kontext-Surfaces aus dem bestehenden App-Icon abgeleitet und die
  Shell, Interaktionsfarben sowie zentrale Komponenten damit harmonisiert.
- Wiederverwendbare, nicht semantische Dialog-Kontextrollen fuer Beobachtung,
  Bericht, LEG und neutrale Dialoge eingefuehrt; keine lokalen Dialog-
  Stylesheets oder neuen Arbeitsablaeufe ergaenzt.
- Sidebar und aktive Hauptnavigation freundlicher abgestuft, Primaeraktionen
  auf Brand Blue und den globalen Fokus auf Brand Teal ausgerichtet.
- Dashboard- und Schuelerprofilakzente kontrolliert an die Markenpalette
  angenaehert; Stammdaten, Einstellungen, Tabellen und Dokumentflaechen bleiben
  ueberwiegend neutral.

### Not changed

- Keine Fachlogik, Datenmodelle, SQLite-, Repository-, Service-, Adapter-,
  ViewModel-, Navigations-, Workflow-, Kursfarben-, Bewertungs-,
  Dokumentations- oder Statuslogik geaendert.
