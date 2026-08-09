# Architekturentscheidungen

## ADR-100 - Cipher-Pilotbackups sind same-installation und enden im Restore-Staging

**Status:** Angenommen und ausschließlich im bestehenden internen
Final-V3-SQLCipher-Gate lokal implementiert. Keine UI-, Produkt-, Build- oder
Releaseaktivierung; kein Live-Austausch.

### Entscheidung

Der frische verschlüsselte Final-V3-Pilotbestand verwendet ausschließlich
`.jkmebackup`. Unter dem vorhandenen Maintenance-Gate und
`ObservationWriterLock` werden Haupt- und Companion-SQLCipher-Datenbank über
ihre keyed Backup-API konsistent snapshotiert. Unter demselben eingefrorenen
Zustand werden alle Companion-registrierten `.jkmedoc`-Generationen gesichert
und die exakt aktive Teilmenge gegen allgemeine Schülerdokumente,
Beobachtungsanhänge sowie RPA-/LCA-Referenzen der Hauptdatenbank gebunden.

Das authentisiert verschlüsselte Manifest bindet Installation- und
Database-Context, Keyset- und Database-Key-Envelope-Generationen ohne
Schlüsselmaterial, DB-Rollen, Engine-/Schemaversionen, Größen, SHA-256 sowie
das vollständige Dokumentinventar. Keyset-Metadaten werden einschließlich WAL
über die SQLite-Backup-API gesnapshotiert; die Envelope-Registry wird als
bereits kryptografisch geschützte Reopen-Metadaten aufgenommen. `security.sqlite`,
DMK, App-Passwort, Recovery-Codes, Device-Credential, Touch-ID-Zustand,
Keychain-Secrets, Logs, UI-Präferenzen und Testartefakte sind ausgeschlossen.

Der vorhandene Backup-Key-Vertrag bleibt zweckgetrennt: DMK → eigene
Backup-HKDF-Domain → zufälliger 256-Bit-Backup-Key → AES-GCM-Envelope →
Secretstream XChaCha20-Poly1305. Database-Key, Document-Key und deren
Wrapping-Keys werden nicht wiederverwendet. Writer und Verifier erzwingen
No-Clobber, Recordreihenfolge, Final-Tag, physisches EOF und vollständige
Neuprüfung vor Veröffentlichung.

Restore extrahiert ausschließlich in einen neuen privaten Staging-Root. Erst
nach keyed Reopen beider SQLCipher-Datenbanken, exakter 4.17-/Schema-/Context-
Prüfung, vollständiger `.jkmedoc`-Verifikation und allen Crossbindings wird
`RESTORE_READY` geschrieben. Dieses Paket führt weder Rename noch Live-Swap,
Neustart oder Produktaktivierung aus.

### Portabilitätsgrenze

Restore ist bewusst ein `same-installation encrypted restore`: Der passende
DMK muss im vorhandenen Keychain verfügbar sein. Passwortwechsel und
Support-Reset rotieren ihn nicht und brechen den Reopen deshalb nicht. Verlust
des DMK oder kompletter Geräteverlust ist kein gelöstes Portable-Recovery-
Szenario. Es wird kein Passwort- oder Recovery-Code-basierter Ersatzschlüssel
eingeführt.

Historische Klartextbestände, ZIP-v1-Backups und alte Testdaten werden weder
migriert noch gelesen. Gate-Off behält bis zu einem späteren
Produktaktivierungspaket unverändert ZIP-v1.

## ADR-099 - Dokumentgenerationen nutzen eine kontextgebundene SQLCipher-Companion-DB

**Status:** Angenommen und ausschließlich im bestehenden internen
Final-V3-SQLCipher-Gate lokal implementiert. Beobachtungsanhänge und neue
allgemeine verwaltete Schülerdokumente verwenden denselben Store.
Produktaktivierung, PDF-Artefakte, Export, Backup/Restore, Migration, Build und
Release bleiben ausgeschlossen.

### Entscheidung

Die Dokumentcontainer-Runtime verändert weder das Final-V3-Hauptschema noch
dessen exakten Fingerprint. Sie verwendet im selben doppelt markergebundenen
privaten Runtime-Root eine eigene SQLCipher-Companion-Datenbank mit
`application_id`, `user_version=1`, fest registriertem Schemafingerprint und
Bindung an `installation_id` sowie `database_context_id`. Derselbe vorhandene
zufällige Database-Key öffnet beide Datenbanken über getrennte strikt
pfadgebundene Factories; Standard-SQLite und Klartextfallback bleiben
ausgeschlossen.

Jede unveränderliche Dokumentgeneration besitzt eine technische Document-ID,
opaque Storage-ID, eigene zufällige Document-Key-ID/-Generation, Envelope-
Revision, Containerformat, Größen-/Hashnachweise, MIME-Typ und genau einen
Lifecycle `PREPARED`, `ACTIVE`, `RETAINED` oder `QUARANTINED`. Ein Pointer und
ein partieller Unique-Index erzwingen genau eine aktive Generation je bereits
aktiviertem Dokument. Der Dateiname besteht ausschließlich aus Storage-ID und
`.jkmedoc`; Originalname und fachliche Metadaten liegen nur in SQLCipher und
im verschlüsselten Manifest, Fachinhalt nur im verschlüsselten Container.
Für Beobachtungsanhänge und allgemeine Schülerdokumente ist die technische
Document-ID unmittelbar die fachlich stabile `MED-######`-ID. UUID4 bleiben
für Storage-, Container-,
Document-Key-, Installations- und Database-Context-Identitäten zwingend.

`prepare` veröffentlicht no-clobber einen vollständig verifizierten Container
vor dem `PREPARED`-Write. `activate` verifiziert erneut und schaltet Pointer,
neue aktive sowie alte retained Generation in einer `BEGIN IMMEDIATE`-
Transaktion um. `read` besitzt keinen Exportpfad und streamt nur an einen
injizierten Consumer. Unbekannte Container, Teilbestände, Symlinks,
Kontextabweichungen und Manipulation blockieren; keine Generation wird still
neu erzeugt, überschrieben oder physisch gelöscht.

Weil Final-V3-Hauptdatenbank und Companion-DB keine gemeinsame Transaktion
besitzen, bindet das vorhandene Observation-Journal vor dem Containerwrite
den unveränderlichen Cipher-Speichermodus, MED-ID, vorherige aktive Generation,
geplante Generation und opaque Storage-ID. Eine Recovery ohne dieselbe Runtime blockiert. Nach verifiziertem
`PREPARED` schreibt die Observation-UoW Beobachtung, Ratings, Ereignisse und
fachliche Dokumentreferenz atomar in Final-V3. Erst danach werden alle exakt
gebundenen Aktivierungen und Deaktivierungen eines Journals gemeinsam in einer
Companion-SQLCipher-Transaktion angewendet. Entfernen deaktiviert die
fachliche Referenz und setzt den Companion-Pointer auf inaktive retained
Generationen zurück; Container werden nicht gelöscht.

Allgemeine Schülerdokumente verwenden denselben `ManagedDocumentStore` über
einen eigenen kleinen fachlichen Application-Service. Dessen Journal enthält
nur Operation, MED-ID, Prepare-Plan und Hashbindung, während Originalname,
Titel, Typ, Notiz und Schülerbezug ausschließlich in SQLCipher beziehungsweise
dem verschlüsselten Manifest liegen. Das vorhandene Final-V3-`documents`-
Schema trägt den Vertrag mit `observation_id IS NULL` und leerem `file_path`;
eine parallele Dokumenttabelle entsteht nicht.

Der Pilot startet ausschließlich mit einem frischen verschlüsselten Final-V3-
Bestand. Es wird keine Klartextmigration, Altbestandskonvertierung oder
Kompatibilitätsschicht für alte Testdaten implementiert; Testdaten werden nach
Verschlüsselungsaktivierung neu erzeugt. Gate-Off bleibt unverändert.

### Folgen

Der bestehende Final-V3-SQLCipher-Restart und Hauptschemafingerprint bleiben
unverändert. Die Companion-Datenbank darf nur in einem ausdrücklich zum
Neuanlegen autorisierten internen Aufruf entstehen; Restart erzeugt fehlende
Bestände nicht nach. Prozessabbrüche vor Persistenz blockieren bei Orphans,
während `PREPARED` und nicht committete Pointerwechsel exakt fortsetzbar sind.

## ADR-098 - Final-V3-SQLCipher nutzt eine einzige keyed Providerkomposition

**Status:** Angenommen und ausschließlich im internen markergebundenen Gate
lokal implementiert. Produktaktivierung, Migration, Dokumentverschlüsselung,
Backup/Restore, Build und Release bleiben offen.

### Entscheidung

Der vorhandene zufällige Database-Key aus der DMK-/Envelope-Runtime wird im
zusätzlich markergebundenen technischen First Run an genau einen expliziten
SQLCipher-4.17-Provider gebunden. Diese Factory ist die gemeinsame
Öffnungsgrenze für direkte Final-V3-Schemaerzeugung, keyed
Kompatibilitätsprüfung, `SQLiteDatabase`, Repositories und Desktop-Adapter.
Standard-`sqlite3`, SQLCipher 4.12, App-Passwort oder DMK als Datenbankschlüssel
und jeder Create-Fallback sind in diesem Pfad ausgeschlossen.

Eine Neuanlage ist nur bei gemeinsam fehlendem Datenbank-, Keyset- und
Envelopebestand, bestätigter Authentifizierung, expliziter technischer
First-Run-Bestätigung und einem im selben Aufruf neu aktivierten Database-Key
zulässig. Restart verlangt den vollständigen Bestand und prüft die Datenbank
zuerst read-only keyed auf Cipher-/SQLite-Version, Cipherstatus, Integrität,
Foreign Keys, `user_version` und vollständigen Final-V3-Fingerprint. Jede
Asymmetrie und jeder Crashrest blockiert oder wird nur nach vollständiger
erneuter keyed Prüfung akzeptiert; es gibt keine Reparatur oder Migration.
Coordinator und Factory sind keine Umgehung des Gates: beide revalidieren den
markergebundenen Temp-Root und die exakt abgeleiteten Pfade. Die Prüfung nach
First-Run-Commit erfolgt über eine neue read-only keyed Connection derselben
Factory; echte Prozessabbrüche belegen die fünf Crashgrenzen.

### Folgen

Das Final-V3-Fachdatenmodell erhält kein Security-Kontextfeld. Der bestehende
Keyset-/Envelope-`database_context_id` bleibt die technische Kryptobindung.
Das Gate wird nicht in Shell oder Produkt-Composition-Root importiert und
öffnet ausschließlich den festen Bestand innerhalb des privaten doppelt
markierten System-Temporärroots.

## ADR-097 - Produktive Writer drainen über ein zentrales In-Process-Maintenance-Gate

**Status:** Angenommen und mit SJ-3C.3 lokal implementiert. Produktive
Ausführung des Schuljahreswechsels, Backup, Authentifizierung und UI bleiben
offen.

### Entscheidung

Die Composition Root besitzt genau ein Qt-freies `MaintenanceGate`. Jede
produktive fachliche SQLite-Connection wird durch dieselbe Gateinstanz
geschützt. Neue Writer erhalten ausschließlich in `NORMAL` eine reentrante
`WriterLease`. Der Wechsel nach `MAINTENANCE_PENDING` ist nicht blockierend:
ab dann beginnen keine neuen Writer, während bereits zugelassene
mehrstufige Datei-/Datenbankaggregate ihre Folgeschritte kontrolliert
abschließen dürfen. `MAINTENANCE_ACTIVE` ist ausschließlich bei Writerzahl
null zulässig.

Der Maintenancebesitz wird durch eine nicht fälschbare
`MaintenanceCapability` an Owner und Zweck gebunden. Nur eine ACTIVE
Capability mit Zweck `SCHOOL_YEAR_TRANSITION` autorisiert die isolierte
Transition-Transaktion. Backup/Restore besitzt den davon getrennten
reservierten Zweck `BACKUP_RESTORE` und wird in SJ-3C.3 nicht an das Gate
angeschlossen. Ein unklarer interner Zustand wechselt fail-closed nach
`RECOVERY_REQUIRED`; dieser Zustand lässt weder Writer noch normale
Gatefreigabe zu.

Die äußere Lease umfasst bei Beobachtungsanhängen, Dokumentimport,
Berichts-/LEG-PDF und mehrstufigen Stammdatenwrites den vollständigen
Produktvorgang. Die gemeinsame Connection-Grenze schützt zusätzlich jeden
fachlichen SQLite-Write. Reads bleiben in allen Gatezuständen zulässig. Das
Gate selbst persistiert nichts und pumpt oder besitzt keinen Qt-Eventloop.

### Grenzen

SJ-3C.3 startet keinen Backupworkflow, fragt kein Passwort ab, ergänzt keinen
Ausführungsbutton und verdrahtet `ExecuteSchoolYearTransition` nicht in Shell
oder Settings. Securitydaten, Apppräferenzen, Support-Reset, Updatezustand
und bewusste Exporte sind keine schuljahreskonsistenzrelevanten Fachwriter
und bleiben ohne neue Auth-/Security-Integration außerhalb dieses Gates.

## ADR-096 - V3 ist das erste und einzige Produktschema

**Status:** Angenommen. Diese Entscheidung ersetzt die V2-Cutover-,
V2-Bootstrap- und V2-Restore-Annahmen aus ADR-095. Der fachliche
Schuljahres- und Assignmentvertrag aus ADR-095 bleibt bestehen.

### Kontext

Es existieren keine produktiven V2-Daten. Alle bisherigen V2-Bestände sind
synthetische Entwicklungsdaten und dürfen verworfen sowie direkt im finalen
Schema neu erzeugt werden. Echte Nutzerdaten werden erst nach vollständiger
Implementierung, Prüfung und ausdrücklicher Freigabe des finalen Schemas
verwendet.

### Entscheidung

V3 ist das erste und einzige Produktschema. Es enthält mindestens
`school_years`, `student_school_year_assignments`,
`courses.year_level`, `students` ohne `group_id` und `course_id` sowie
`school_year_transitions` für echte spätere Schuljahreswechsel.

Es gibt keinen produktiven V2→V3-Cutover, keine V2-Klassifizierung, keinen
V2-Migrationsplan, keinen V2-Backupnachweis für einen Cutover, keinen
V2-Bootstrap-Assistenten, keinen V2-Produktrestore und keine dauerhafte
V2-Kompatibilitätszusage. Alte oder unbekannte Datenbankschemata werden nicht
übernommen, sondern fail-closed abgelehnt.

Eine fehlende Datenbank darf nur in einem kontrollierten, ausdrücklich
autorisierten First-Run- oder temporären Testkontext direkt als vollständiges
V3-Schema erzeugt werden. Dabei wird kein Übergangsbeleg geschrieben. Solange
produktive Leser und Writer noch V2-Mitgliedschaftsfelder erwarten, bleibt die
normale Shell trotz erkanntem finalem Schema gesperrt; der Zwischenzustand
wird ausdrücklich als `V3_SCHEMA_READY_BUT_RUNTIME_NOT_MIGRATED` oder
gleichwertig benannt.

`school_year_transitions` dokumentiert ausschließlich echte
Schuljahreswechsel zwischen zwei vorhandenen Schuljahren.
`from_school_year_id` und `to_school_year_id` sind deshalb in einem
produktiven Übergang beide gesetzt. Eine Initialanlage mit
`from_school_year_id = NULL` ist kein zulässiger Übergang.

Backupformat und Datenbankschema sind getrennte Verträge. Backup und Restore
bleiben als Sicherheitsfunktionen erhalten, akzeptieren als Produktdatenbank
aber ausschließlich das exakte finale Schema. Vorschau, verifiziertes Backup,
Maintenance-Gate, atomare Transaktion, Rollback, Idempotenz und Historie
bleiben für den späteren echten Schuljahreswechsel verbindlich.

### Folgen

Die V2→V3-Migrationsengine, ihre Cutover-Zustände, Failpoints,
Backup-Evidence und exklusiven Tests werden durch neue Commits entfernt.
Finales DDL, Fingerprint, Constraints, Trigger und Indizes werden in eine
direkte V3-Schemaquelle überführt. Synthetische Testbestände werden
deterministisch und ausschließlich in temporären Datenbanken neu erzeugt.
Produktive V3-Leser, Writer, Assignment-API, Schuljahreswechsel und
Runtime-Freigabe sind gesonderte nachfolgende Arbeit und werden durch diese
Entscheidung nicht als implementiert behauptet.

## ADR-095 - Schuljahre und datierte Schülerzuordnungen bilden die einzige Mitgliedschaftswahrheit

**Status:** Teilweise durch ADR-096 ersetzt. Weiterhin verbindlich sind das
finale Fachmodell, die Datenhoheit, datierte Zuordnungen, echte
Schuljahreswechsel und deren Sicherheitsgrenzen. Verworfen sind alle
Legacyklassifizierungs-, V2-Cutover-, Bootstrap- und V2-Restore-Annahmen.

### Datenhoheit und Invarianten

`school_years` ist die einzige dauerhafte Source of Truth für Schuljahre.
`student_school_year_assignments` ist die einzige dauerhafte Source of Truth
für aktuelle und historische Kurs- und Stammgruppenzuordnungen. Die
`students`-Tabelle enthält keine Mitgliedschaftsfelder.
`courses.year_level` trägt ausschließlich die stabile fachliche Stufe 1, 2
oder 3; Name, Sortierung und UI-Position sind keine Ableitungsquellen.

Ein Schuljahr besitzt einen nicht leeren, geschlossenen Datumsbereich und den
Status `planned`, `current` oder `closed`. Bereiche überlappen sich
nicht, genau ein fachlich aktiver Bestand besitzt ein `current`-Schuljahr,
und geschlossene Jahre sind unveränderlich. Das Systemdatum aktiviert,
schließt oder verschiebt niemals automatisch ein Schuljahr.

Ein Assignment liegt vollständig innerhalb seines Schuljahres. Intervalle
desselben Kindes überlappen sich nicht.
`assignment_status = enrolled` verlangt Gruppe und Kurs;
`assignment_status = exited` besitzt weder Gruppe noch Kurs und archiviert
das Kind nicht. Unterjährige Kurs- oder Stammgruppenwechsel beenden das alte
Intervall am Tag vor dem expliziten Stichtag und beginnen das neue am
Stichtag.

### Historische Auflösung

Aktuelle und historische Zuordnungen werden an einem ausdrücklich übergebenen
fachlichen Referenzzeitpunkt aufgelöst: Beobachtung über
`observations.date`, Bestätigung über `confirmed_at`, Bericht über
`period_end`, LEG über `conference_date` und ein
Beobachtungsdokument über das Datum der referenzierten Beobachtung. Ohne
belastbares Datum wird keine Zuordnung erfunden. Finalisierte Bericht- und
LEG-Revisionen sowie PDFs bleiben unveränderlich.

### Echte Schuljahreswechsel

Ein Schuljahreswechsel führt von einem vorhandenen aktuellen Schuljahr zu
einem bewusst festgelegten Zielschuljahr. Dessen Daten bleiben vor der
atomaren Ausführung flüchtiger Planbestand und werden erst innerhalb der
Wechseltransaktion als neues `current`-Schuljahr angelegt. Kursvorschläge
verwenden ausschließlich `courses.year_level`; Stufe 3 bleibt bis zu einer
bewussten Entscheidung ungelöst. Stammgruppen bleiben ohne ausdrückliche
Änderung unverändert. Austritt, Archivierung und physische Löschung bleiben
getrennte Vorgänge.

`school_year_transitions` belegt nur einen erfolgreich committed echten
Wechsel. Der Beleg enthält vorhandene Ausgangs- und Zielschuljahr-IDs, einen
Operation-Token, Plan- und Backupnachweis, Ergebniszahlen und
Abschlusszeitpunkt. Derselbe Token mit demselben Plan ist idempotent; ein
abweichender Plan wird abgelehnt.

Der Ablauf bleibt Maintenance-gebunden: Schreibzugriffe sperren, offene
Editoren sicher behandeln, verifiziertes Backup erstellen, Plan und Quellen
erneut prüfen, Passwort-Step-up und explizite Bestätigung verlangen, genau
eine `BEGIN IMMEDIATE`-Transaktion ausführen, Ausgangsjahr schließen,
Zieljahr aktivieren, Assignments und Übergangsbeleg schreiben, Integrität
prüfen und bei jedem Fehler vor Commit vollständig zurückrollen. Der Assistent
und seine Runtime-Aktivierung sind noch nicht implementiert.

Unterjährige Sammelwechsel verwenden ebenfalls einen gemeinsamen expliziten
Stichtag, vollständige Vorschau, erneute Validierung und eine atomare
Transaktion. Sie erzeugen keinen
`school_year_transitions`-Beleg und sind noch nicht implementiert.

## ADR-094 - Phase-2-Berichte-Übersicht ist eine rein lesende Belegprojektion

**Status:** Angenommen als Zielarchitektur; nicht implementiert.

Die Phase-2-Berichte-Übersicht unterstützt die Berichtsvorbereitung, indem sie
vorhandene Beobachtungen, Belege und reale Dokumentereignisse im gewählten
Berichtszeitraum neutral zusammenführt. Sie ist keine Entwicklungsanalyse und
erzeugt weder einen Themenverlauf noch einen Kompetenzentwicklungs-Drill-down,
eine automatische Entwicklungszusammenfassung oder eine automatische
Berichtsformulierung. Der bestehende Profilbereich `Überblick` bleibt
Eigentümer der kompakten Lernentwicklungsdarstellung; `Kompetenzen` bleibt
Eigentümer der detaillierten Kompetenz- und Belegansicht.

Die Oberfläche darf unterstützen, aber niemals pädagogische Entscheidungen
treffen. Stärke, Schwäche, Defizit, Förderbedarf, Trend, Wichtigkeit,
pädagogische Relevanz und automatische Priorität werden weder abgeleitet noch
sichtbar behauptet.

Die Projektion verwendet ausschließlich vorhandene kanonische Lesequellen:
den eindeutig gewählten RPD als alleinige Zeitraumquelle, die getrennten
Bericht- und LEG-Pfade des Schülers, aktive Beobachtungen mit vorhandenen
Kompetenzzuordnungen sowie die kanonische Projektion des aktuellen Kompetenz-
und Bestätigungsstands. Sie führt keine Tabelle, Migration, gespeicherte
Timeline, neue fachliche Datenquelle oder neue Statuslogik ein.

`period_start` und `period_end` des eindeutig gewählten RPD bilden den einzigen
inklusiven Zeitraumvertrag. Schuljahr, Halbjahr, Kalenderjahr, Tagesdatum,
LEG-Zeitraum oder andere RPD sind keine Fallbacks. Fehlende oder ungültige
Datumswerte werden nicht ersetzt; betroffene Inhalte bleiben aus der
Zeitraumprojektion ausgeschlossen und führen zu einem neutralen
Unvollständigkeitszustand. Ohne eine bewusst getroffene, weiterhin gültige
Auswahl entsteht keine Phase-2-Projektion; weder ein einzelner vorhandener RPD
noch eine veraltete Auswahl wird automatisch ersetzt oder aktiviert.

Die flüchtige Ereignisprojektion verwendet ausschließlich folgende stabile
Identitäten:

- eine aktive Beobachtung höchstens einmal als
  `("observation", observation_id)`;
- ein fachlich abgeschlossenes Berichtaggregat höchstens einmal als
  `("report", report_draft_id)`;
- ein tatsächlich durchgeführtes und fachlich abgeschlossenes LEG-Aggregat
  höchstens einmal als
  `("learning_conference", learning_conference_draft_id)`;
- den aktuell vorhandenen sicheren Bestätigungsstand höchstens einmal als
  `("confirmation", student_id, competency_id)`.

Vorhandene Paare `(observation_id, competency_id)` bleiben Grundlage für
Fachkartenzählung, Kompetenzsegmente, Belegdetails, Fachzuordnung und
Deduplizierung. Sie erzeugen keine eigenen Timeline-Ereignisse. Eine
Schnellbeobachtung ohne Zuordnung bleibt eine Beobachtung und erzeugt keine
dokumentierte Kompetenz.

Für ein Berichtaggregat wird ausschließlich die neueste gültige,
hashverifizierte Revision als sichtbarer Stand und Navigationsziel verwendet;
deren `finalized_at` ist der fachliche Timeline-Zeitpunkt. Frühere technische
Revisionen bleiben in der Revisionshistorie und erzeugen keine zusätzlichen
Timeline-Karten. Für ein LEG-Aggregat wird ebenfalls ausschließlich die
neueste gültige, hashverifizierte Revision als Navigationsziel verwendet. Das
fachliche Timeline-Datum ist `conference_date`; `completed_at` bleibt ein
technischer Lifecycle-Zeitpunkt. Frühere LEG-Revisionen bleiben in der
LEG-Revisionshistorie.

Draft-Öffnen, Draft-Speichern, `updated_at`, technische Bearbeitungs- oder
Verwaltungszeitpunkte, Zwischenstände, Revisionen als solche,
`orientation_changes`, `persistence_events`, Hashes, Sequenzen und
Operation-Token sind keine Timeline-Ereignisse. Der Zielumfang beträgt 15
Ereignisse. Liegen weniger als 15 verpflichtende Bericht-/LEG-Ereignisse vor,
wird die Timeline mit den zeitlich neuesten zulässigen Beobachtungs- und
aktuellen sicheren Bestätigungsereignissen aufgefüllt. Liegen mindestens 15
gültige Bericht-/LEG-Aggregatereignisse vor, bleiben alle enthalten und es
werden keine ergänzenden Ereignisse aufgenommen; 15 ist für Dokumentereignisse
keine Obergrenze.

Ergänzende Ereignisse werden ausschließlich nach fachlichem Zeitpunkt und bei
Zeitgleichheit nach stabiler technischer Quellidentität in aufsteigender
lexikografischer Reihenfolge ausgewählt. Die gesamte ausgewählte Menge wird
anschließend chronologisch vom ältesten zum neuesten Ereignis geordnet; bei
identischem fachlichem Zeitpunkt gilt erneut die aufsteigende lexikografische
Quellidentität. Diese Auswahl ist unabhängig von Rating, Fach, Ereignistyp
außerhalb der verpflichtenden Bericht-/LEG-Aufnahmeregel, Wichtigkeit, Stärke,
Defizit, Förderbedarf, pädagogischer Relevanz oder automatischer Priorität.

Bestätigungen stammen ausschließlich aus dem aktuell gespeicherten, kanonisch
sicheren Stand einer aktiven, nicht historischen Kompetenz.
`confirmation_unknown` ist kein sicherer Bestätigungsstand. Eine historische
Bestätigungskette wird nicht rekonstruiert. `persistence_events` bleibt die
technische Grundlage für Frische und Wiederanlauf gemäß ADR-089, ist aber
keine pädagogische Timeline-Quelle. Rating, Ratingwechsel,
Bestätigungsfrische, Trend und Entwicklungsrichtung sind keine
Ereignisinhalte.

Fachbezogene Dokumentationsmengen werden als Mengen stabiler Kompetenz- und
Beobachtungsidentitäten im RPD-Zeitraum gebildet. Sie besitzen keinen
curricularen Nenner, keine Restspur, Prozent- oder x/y-Semantik,
Normalisierung, Schwelle oder Bewertungsbedeutung. Mit vorhandenen
Kompetenzzuordnungen entsteht die Fachmenge ausschließlich aus deren
tatsächlichen `subject_id`; `observations.subject_id` ist dann kein Fallback.
Ohne Zuordnung wird ausschließlich `observations.subject_id` verwendet.
`cross_subject` erzeugt keine Fachkarte. Historische oder deaktivierte
Kompetenzen zählen nicht zum aktuellen Kompetenzbestand und erzeugen kein
aktuelles Bestätigungsereignis; zugehörige reale aktive Beobachtungen bleiben
nach ihrem eigenen Identitätsvertrag lesbar.

`StudentDesktopAdapter.report_overview_for_student` bleibt die
Kompositionsgrenze. Repositories und Application Services behalten ihre
bestehenden fachlichen Zuständigkeiten. Die reine ViewModel-Projektion besitzt
Filterung, Datumsnormalisierung, Deduplizierung, deterministische Auswahl,
Chronologie und displayfertige neutrale Zustände und liefert die vollständige
ausgewählte Timeline-Liste. Das Widget besitzt keine Zeitraum-, Ereignis-,
Zähl-, Bestätigungs-, Historien- oder Relevanzentscheidung. Es rendert die
Liste horizontal scrollbar, startet am neuesten Ende und ermöglicht bewusstes
Scrollen zu älteren Ereignissen. Ungefähr zwei, vier oder fünf gleichzeitig
sichtbare Karten sind ausschließlich Viewportzustände und keine
Inhaltsauswahl; automatisches Karussell und automatische Bewegung sind
ausgeschlossen.

Bericht und LEG bleiben nach ADR-050 sowie ADR-052 bis ADR-057 getrennte
Aggregate, Repositories, Application Services, Revisionen, Lifecycle- und
Integritätsverträge. Ihre gemeinsame Anzeige ist ausschließlich eine
Displaykomposition. ADR-051 bleibt für Schnellbeobachtungen ohne automatische
Kompetenzzuordnung verbindlich; ADR-089 bleibt technische Wahrheit für
Persistenzreihenfolge und Wiederanlauf.

Der gesonderte Product-Owner-Auftrag vom 29. Juli 2026 gibt ausschließlich die
kontrollierte lokale Umsetzung und Prüfung der Pakete 2A.1, 2A.2, 2B und 2C
frei. Datenmodelländerung, Migration, Build, Packaging, Push, Tag und Release
bleiben ausgeschlossen.

## ADR-093 - Security-Funktionen werden im Bundle nur über doppelt gegatete interne Smokes geprüft

**Status:** Angenommen für Security Sprint 12 und den internen
macOS-arm64-Testbuild 0.3.0; keine Produkt-, Pilot- oder Releaseaktivierung.

Der normale App-Start bleibt Gate-Off und importiert weder den
Sprint-11-Orchestrator noch die Pakettestrunner. PyInstaller nimmt die
erforderlichen SQLCipher-, PyNaCl/libsodium-, cffi- und Integrationsmodule
dennoch explizit auf. Nur ein eigener Kommandozeilen-Testeinstieg zusammen mit
dem bestehenden Paketmarker, dem exakten Sprint-11-Gatewert und einem privaten
doppelt markierten System-Temporärroot darf den Gate-On-Pfad laden. Dadurch
wird die echte Bundleauflösung geprüft, ohne einen normalen Startuphook oder
eine UI-Aktivierung einzuführen.

Der Gate-On-Smoke verwendet ausschließlich synthetische Daten und an die
temporäre Rootidentität gebundene deterministische Testschlüssel. Er prüft
Migration, verschlüsselte Dokumente und Backups, Restore-Staging, Reopen,
falschen Schlüssel, manipulierte Artefakte, Gate-Off bei vorhandenem Bestand
und repräsentative echte Prozessabbrüche. Diese Testschlüssel sind weder
Produkt- noch Pilotkeys und verlassen den temporären Testbestand nicht.

Ein zweiter Testeinstieg prüft den realen macOS-Keychain-DMK-Port in einem
separaten künstlichen Security-Root. Der Test widerruft und löscht seinen
Eintrag am Ende. Physische Touch ID, verweigerter Nutzerzugriff,
Developer-ID-/Notarisierungsübergang und eine tatsächlich neue signierte
Buildversion bleiben manuelle reale Gates.

Der macOS-Build pinnt `sqlcipher3` 0.6.2 / SQLCipher Community 4.12.0 und
PyNaCl 1.6.2 ausschließlich für diesen internen inaktiven Testpfad. Das ist
keine Ersetzung des dokumentierten SQLCipher-4.17.0-Produktziels. Eine
automatische oder produktive Migration bleibt gesperrt. Das fertige Bundle
wird vor Codesign auf arm64 reduziert und danach auf Version, native
Abhängigkeiten, Lizenztexte, verbotene Artefakte und Entwicklerpfade geprüft.

Windows besitzt weiterhin keinen implementierten DPAPI-Adapter und keine
reale E2E-Abnahme. Ein unsupported/fail-closed Port darf nicht als
Windows-Freigabe umgedeutet werden.

## ADR-092 - Sprint 11 integriert nur in einem markergebundenen Test-Root

**Status:** Angenommen für den standardmäßig inaktiven Security-Sprint-11-
Integrationspfad; keine Pilot-, RC-, Packaging- oder Releasefreigabe.

Der Standardpfad bleibt Klartext-SQLite plus bestehender Dokument- und
ZIP-v1-Backup-/Restorelogik. Ausschließlich
`JKM_SECURITY_INTEGRATION_TEST=1` zusammen mit einem privaten,
eigentümergeprüften, doppelt markierten Root unter der
System-Temporärwurzel aktiviert den Integrationspfad. Die Umgebungsvariable ist
kein dauerhaftes Produktkonzept. Es gibt keine UI, automatische Aktivierung
oder stille Engineumschaltung.

Im Integrationspfad ist eine zentrale Connection Factory die einzige
Fachdatenbank-Öffnungsgrenze. SQLCipher-Keying, Engine-/PRAGMA-/Schema- und
Integritätsprüfung erfolgen vor fachlichem Zugriff; bestehende Ziele werden
mit `create=False` geöffnet. Falscher oder fehlender Key darf keine
Klartextdatei erzeugen. Der Transfer bleibt ohne Identity-VFS, Capability-
Code, `ATTACH` und `sqlcipher_export`.

Die kleinste Schemaerweiterung besteht aus einer eindeutig versionierten
Integrationsmetadatenzeile und einer historischen
`security_document_generations`-Tabelle. Sie hält technische Document-ID,
opaque Storage-ID, Dokument-/Key-Generation, Key-ID, Envelope-Revision,
Containerformatversion, Klartextgröße/-hash, MIME-Typ, Lifecycle sowie
Retained-/Quarantänegrund. Originalname und fachliche Metadaten bleiben in der
verschlüsselten `documents`-Tabelle beziehungsweise im verschlüsselten
Manifest. Ein partieller Unique-Index erlaubt genau eine aktive Generation je
Dokument. `user_version=1101` macht den Testbestand rückwärts eindeutig
erkennbar.

Dokumentcontainer werden vollständig geschrieben und verifiziert, bevor eine
SQLCipher-Transaktion alle Pointer umstellt. Backup umfasst nur die frisch
validierte SQLCipher-Datei und verschlüsselte Dokumentcontainer. Restore
endet in einem neuen vollständig geprüften Staging-Root; eine Produkt-Live-
Umschaltung bleibt gesperrt.

Ein HMAC-authentisiertes Journal und ein vom Integrationsroot getrennter
pending/committed Replay-Anker binden IDs, Generationen, feste Rollen, relative
Pfade, Größen und Hashes. Recovery beginnt in einem neuen Prozess, wiederholt
nur idempotente Schritte und blockiert unbekannte oder gemischte Zustände.
Klartextquelle und Safety Copy werden erst nach `REOPEN_VERIFIED` als Retained
markiert und nicht automatisch gelöscht.

Support-Reset und Passwortwechsel ersetzen weder DMK noch Database-,
Document- oder Backup-Key. Der bestehende Supportprozess bleibt unverändert.
Eine fehlende oder beschädigte Plattformschlüsselablage blockiert ohne stille
Schlüsselerneuerung.

Ein Sprint-11-GO gilt ausschließlich für diesen inaktiven Testpfad. Windows,
Packaging, Notarisierung, reale Produktmigration, physisches GC und Release
bleiben NO-GO. Es wird keine rechtliche Compliance-Aussage getroffen.

## ADR-091 - Eigenes Secretstream-Dokumentformat mit integriertem Envelope

**Status:** Angenommen für den isolierten synthetischen
Security-Sprint-10-Nachweis; keine Produktaktivierung und keine Änderung
bestehender Dokument-, Viewer-, Export- oder Backup-/Restore-Pfade.

Der Dokumentcontainer verwendet wie der isolierte Backupnachweis
`libsodium-secretstream-xchacha20poly1305`, aber ein vollständig eigenes
Dokumentformat, eine eigene HKDF-Domain, eigene Envelope-/Record-AAD,
Dokumentmetadaten und Fehlercodes. Backup-Envelope, -Header, -Manifest und
-Container sind keine Dokumenttypen. Secretstream wurde ausgewählt, weil es
begrenztes Streaming, kryptografisch verkettete Sequenz und einen expliziten
`TAG_FINAL` bereitstellt. Ein eigenes chunked XChaCha20-Poly1305-Protokoll
wurde für v1 verworfen, weil Nonce-Eindeutigkeit, Offset-/Indexauthentisierung,
Sequenz, Trunkierung und Finalität dann zusätzlich selbst entworfen werden
müssten. Sein Vorteil, echtes Random Access, bleibt ein mögliches Format-v2-
Gate für einen späteren Viewer.

Jede Dokumentgeneration besitzt einen zufälligen 256-Bit-Document-Key. Der DMK
leitet per HKDF-SHA-256 einen ausschließlich dokumentbezogenen Wrapping-Key ab;
AES-256-GCM schützt den Document-Key mit frischer Nonce in
`DocumentKeyEnvelopeV1`. App-Passwort, Database-Key, Backup-Key und
Document-Key werden weder gleichgesetzt noch voneinander abgeleitet.

Envelope und Ciphertext liegen in einer Datei. Dies vermeidet Torn States,
Vertauschung und atomare Veröffentlichung zweier Sidecars. Der Header ist
logisch geteilt: Das unveränderliche Payload-Binding enthält Format,
Algorithmen, Container-ID, Document-Key-ID/-Generation, Streamheader und
Chunkvertrag. Secretstream-AAD bindet dessen Digest und den erwarteten
Dokumentkontext, nicht die austauschbaren Nonce-, DMK- oder Ciphertextfelder
des Envelopes. Envelope-AAD bindet Payload-Binding, Dokument-ID/-Generation,
Installation-/Datenbankkontext, DMK-ID/-Generation und Envelope-Revision.
Damit kann ein DMK-Wechsel denselben Document-Key in einer neuen
No-Clobber-Datei rewrappen und den verschlüsselten Payload bytegleich
übernehmen; ein In-place-Rewrap bleibt verboten.

Der sichtbare Header enthält ausschließlich technische Format-, Algorithmus-,
Framing-, Container-, Key-, Envelope- und Streamwerte. Dokument-ID,
Originalname, MIME-Typ, Größe, Klartexthash, fachliche Zuordnung,
Installations-/Datenbankkontext, Erstellungszeit und App-/Formatversion liegen
im verschlüsselten Manifest beziehungsweise später zusätzlich in der
SQLCipher-Fachdatenbank. Der Dateiname verwendet nur eine zufällige opaque
Storage-ID und Envelope-Revision.

Der Recordstrom besteht genau aus einem verschlüsselten Manifest, der
manifestierten Zahl sequenzieller Dokumentchunks und einem leeren
`TAG_FINAL`-Record; physisches EOF ist Pflicht. Reader und Export verifizieren
vor Klartextausgabe vollständig und lesen danach sequenziell erneut. Ein
vollständig gültiger Altcontainer-Replay ist ohne produktiven DB-Pointer oder
externen monotonen Zustand nicht erkennbar. Produkt-Packaging von PyNaCl,
Windows-ACL-/Reparse-Abnahme, echter Power-Loss, Viewer-/Random-Access-UX,
produktive Lifecyclepersistenz und vollständige Schlüssel-Zeroization bleiben
offene Integrations-Gates.

Der isolierte bewusste Klartextexport publiziert sein exklusiv erzeugtes,
verifiziertes Tempziel mit einem plattformspezifisch atomaren
No-Clobber-Rename. Anders als die verschlüsselte Containerpublikation benötigt
er keinen pfadbasierten Temp-Unlink. Normale Fehler leeren ausschließlich den
noch offenen eigenen FD und lassen einen analysierbaren leeren Retained-Eintrag
zurück. Ein Prozessabbruch vor dem Rename kann eine versteckte
Retained-Klartextdatei nur im markergebundenen Exportroot hinterlassen; sie ist
kein erfolgreicher Export. Produktive Restart-Bereinigung und Nutzerführung
bleiben ausdrücklich ein Sprint-11-Gate.


## ADR-090 - Secretstream schützt den isolierten Sprint-9-Backupcontainer

**Status:** Angenommen für den isolierten synthetischen Nachweis; keine
Produktaktivierung und keine Ablösung des bestehenden Backup-/Restore-Pfads.

Der Container verwendet `libsodium-secretstream-xchacha20poly1305` über PyNaCl.
Ein eigenes AES-GCM-Chunkprotokoll wird nicht eingeführt: Secretstream übernimmt
die kryptografische Verkettung sowie die Finalitätsprüfung.

Jeder Container erhält einen zufälligen 256-Bit-Backup-Key. Aus dem DMK leitet
HKDF-SHA-256 einen zweckgetrennten Backup-Wrapping-Key ab; AES-256-GCM schützt
den Backup-Key im streng versionierten Envelope.

Das Format besitzt einen versionierten Header, verschlüsseltes Manifest und
einen strikt geordneten authentisierten Recordstrom mit genau einem Final-Tag.
Unbekannte Versionen oder Algorithmen, Manipulation, Trunkierung, Umordnung,
Duplikation und Zusatzdaten blockieren fail-closed.

Writer, Verifier und Restore bleiben auf einen injizierten synthetischen,
privaten Test-Root begrenzt. Der bestehende `.jkmbackup`-Produktpfad bleibt
inaktiv. Packaging, Windows, realer Power-Loss, Same-User-ABA, Retained-GC und
weitergehende Zeroization sind Folge-Gates.

## ADR-084 - Authentisierte Migrationszustände bleiben eine isolierte Domainfoundation

**Status:** Angenommen für die isolierten Security-7B-Foundations; keine
Produkt- oder Orchestratorfreigabe.

Lockzustände werden als HMAC-authentisierte append-only Transitionskette
persistiert. Jeder Eintrag bindet Vorgänger, Sequenz, Installation,
Datenbankkontext, Migration, Owner, Replay-Anker, Journal und Artefakte.
Wiederaufnahme verlangt den extern erwarteten Kettenkopf und die Sequenz; die
Owner-Evidenz wird nicht durch Truncate ersetzt.

Ein kanonischer `MigrationCrossbindingContext` bindet sämtliche technischen
Migrationsbestandteile. Sein vollständiger Digest enthält den Lockkettenkopf.
Der Lockeintrag bindet umgekehrt einen nicht zirkulären Digest aller übrigen
Kontextfelder. So bleiben Lock-Head und Kontext ohne Digestzyklus prüfbar.

`derive_migration_preflight` bleibt rein, read-only und deterministisch.
Adapter authentisieren ihre Quellen vor der Projektion. Die Domain vergleicht
reale Quelldigests, Revisionen, Identitäten und Generationen mit dem Kontext
und leitet nur `NEW`, `RESUME`, `RECOVERY`, `COMPLETED` oder `BLOCKED`
ab. Widersprüche und unerwartete Artefakte blockieren.

Keine Startup-, Login-, UI-, Backup/Restore-, Produktmigrations- oder
Orchestratorverkabelung wird freigegeben.

## ADR-083 - Ausführende Migrations-Recovery nur unter exklusivem Test-Lock

**Status:** Für Security Sprint 6 ausschließlich im guarded synthetischen
Migrationsprototyp implementiert und nach dem P1-Fix vollständig gegatet. Keine Startup-,
Produktmigrations-, Live-Swap-, Klartextlöschungs- oder Restorefreigabe.

Die reine `MigrationRecoveryEvaluator`-Entscheidung aus ADR-080 bleibt die
fachliche Sicherheitsgrenze. Neu ist ein davon getrennter
`PrototypeMigrationRecoveryOrchestrator`, der nur nach erfolgreicher Entscheidung
und nur in einem explizit injizierten temporären Test-Root mit verifiziertem
Synthetik-Guard wenige allowlistete
Operationen ausführt: Backup erneut prüfen, ein eindeutig identitätsgebundenes
unvollständiges Testziel entfernen, Validierung fortsetzen, ein validiertes
Testziel neu öffnen und bei authentisiertem `COMPLETED` ausschließlich
evidence-gebundenes Ziel und Backup per atomarem No-Clobber-Rename in retained Quarantine
verschieben und dort idempotent identitätsprüfen, aber nicht löschen.
Quelle, Anchor, Registry, Journal, Lock, unbekannte Dateien, produktive Pfade
und reservierte Swap-Phasen sind unveränderlich beziehungsweise blockiert.

Der plattformneutrale `MigrationLockPort` wird im POSIX/macOS-Prototyp durch
`ExclusiveMigrationLock`, in deterministischen Tests durch
`InMemoryMigrationLock` und auf nicht geprüften Plattformen fail-closed durch
`UnsupportedMigrationLock` erfüllt. Jede Operation verlangt einen durch
`ExclusiveMigrationLock` exklusiv angelegten und unmittelbar erneut
verifizierten Lock. Eigentum bindet
Installation, Database-Context, Migration-ID, PID, Prozessstartidentität,
Lock-Nonce, Erstellungszeit und Dateiidentität. PID oder Dateiname allein
reichen nicht. Fremde, manipulierte, ausgetauschte und nicht belastbar stale
Locks werden nicht automatisch entfernt oder überschrieben. Eine kontrollierte
Stale-Übernahme ist nur nach expliziter Prüfung von Prozessstartidentität,
Nonce, Journal und gespeicherter Dateiidentität erlaubt; jede Unklarheit führt
zu `blocked`. Der Takeover verlangt dafür unter dem gehaltenen Kernel-Lock
einen expliziten Recovery-Evidence-Validator; fehlt er, schlägt fehl oder
liefert er nicht exakt `True`, bleibt der Lock unverändert blockiert.

Vor jedem Schritt werden zusätzlich Journal-HMAC, externer Replay-Anker,
Rootgrenze und die aktuelle Dateiidentität geprüft. Kritische Operationen
besitzen einen authentisierten Write-ahead-Zustand und einen nachgelagerten
Beweis. Subprozessabbrüche einschließlich hartem Kill, ENOSPC, fehlende Rechte,
`fsync`-/Rename-/Replace-Fehler und Dateiwechsel zwischen Prüfung und Operation
werden ausschließlich mit synthetischen temporären Daten getestet. Ein Fehler
darf Quelle oder ein gültiges Backup nicht verändern und keine unbekannte Datei
löschen. Auch die separat autorisierte terminale Behandlung verschiebt das
exakt evidence-gebundene Backup nur in retained Quarantine.

Der POSIX/macOS-Prototyp verwendet exklusive Create-Semantik, restriktive
Rechte, Symlinkabweisung und Dateiidentitätsprüfung. Recovery führt für Ziel
und Backup keinerlei pathname-basiertes `unlink` oder `remove` aus; das frühere
finale Unlink-TOCTOU ist beseitigt. Der Quarantäne-Rename verwendet
`RENAME_EXCL` beziehungsweise `RENAME_NOREPLACE` und blockiert auf Plattformen
ohne geprüften No-Clobber-Primitive, sodass ein im Rennfenster erzeugter
fremder Quarantänepfad niemals überschrieben wird. Als P2 verbleibt
ausschließlich retained Quarantine ohne freigegebenen handlebasierten
Bereinigungsprozess; reale
Power-Loss-Sicherheit wird nicht behauptet. Windows benötigt weiterhin ACL-,
Reparse-Point-/Junction-, handlebasierte File-ID-, Replace-/Sharing- und reale
Crashabnahme. Auth-Recovery-Codes und Support-Reset sind andere Domänen und
bleiben byte- und verhaltensgleich.

## ADR-082 - Externer monotoner Security-Anker gegen gültiges Datei-Replay

**Status:** Für Security Sprint 6 als isolierte Security-Foundation
implementiert und nach dem P1-Fix vollständig gegatet; keine RuntimePaths-,
Startup- oder Produktaktivierung.

HMAC und AEAD erkennen Manipulation ohne DMK, nicht aber das gemeinsame
Zurückspielen älterer, damals gültiger Registry- und Journaldateien. Deshalb
liegt der zuletzt akzeptierte Sicherheitsstand hinter dem Plattformport
`MonotonicSecurityAnchorStore` außerhalb dieser replaybaren Dateien. Der
strikte `SecurityAnchorState` bindet Formatversion,
Installation/Security-Context, monotone Anchor-Revision, Database-Context,
DMK-/Keyset-ID und -Generation, Registry-High-Water-Mark,
Journalrevision beziehungsweise Migrationsgeneration sowie die exakten
SHA-256-Digests der bereits authentisierten Registry und des bereits
authentisierten Journals. Er enthält keine Schlüssel, Passwörter, Recovery-
oder Support-Secrets und keine fachlichen Daten.

`initialize` ist ausschließlich ohne vorhandene Security-Artefakte zulässig.
`read`, `compare`, `verify` und `advance` sind idempotent beziehungsweise
atomar; ein Advance akzeptiert nur den erwarteten unmittelbaren Vorgänger und
den vollständig gebundenen neuen Stand. Weil Keychain und Dateisystem keine
gemeinsame atomare Transaktion besitzen, speichert der Anker einen committed
Snapshot und optional genau einen pending Snapshot. Prepare bindet sowohl den
alten committed als auch den exakt geplanten neuen Registry-/Journalstand mit
der Revision committed + 1; die committed Revision wird dabei noch nicht
vorgezogen. Erst danach werden die authentisierten Dateien extern atomar
publiziert. Commit ist nur zulässig, wenn die erneut beobachteten Dateidigests
und sämtliche Kontextbindungen exakt pending entsprechen, und übernimmt genau
die vorbereitete Revision.

Nach Crash darf exakt der alte Dateistand pending durch
`abort_pending(expected, observed_committed)` verwerfen: Der committed
Artifact-Snapshot bleibt erhalten, pending wird entfernt und dessen höhere
Anchor-Revision als monotoner Abbruchnachweis übernommen. Exakt der neue
Dateistand darf den Commit fortsetzen. Abort ist kein Reset. Jeder
partielle, gemischte oder unbekannte Dateistand blockiert. Der
`ExclusiveMigrationLock` serialisiert Prepare, Dateipublikation und
Commit/Abort für denselben Datenbankkontext prozessübergreifend. Rücklauf,
doppelte Revision, unplausibler Sprung, falscher Kontext, Korruption oder
Parallelitätskonflikt blockieren. Ein fehlender oder gelöschter Anker bei vorhandener Registry oder
vorhandenem Journal darf nicht still neu erzeugt werden. `block` wird nicht
automatisch zurückgesetzt; ein späterer Wiederherstellungsprozess braucht eine
eigene Product-Owner- und Recovery-Entscheidung.

macOS speichert den Zustand im eigenen nicht synchronisierenden Keychain-Service
`de.jenaplan.kompetenzmanager.monotonic-security-anchor`. Es gibt keinen
Datei-Fallback. Der In-Memory-Adapter dient ausschließlich deterministischen
Port-, Replay- und Parallelitätstests. Für Windows sind Port, Fehlerklassen,
Fake und ein DPAPI-user-scope-Entwurf zulässig; produktive DPAPI-Persistenz,
Credential-Manager-/ACL-Entscheidung und reale Windows-Prüfung bleiben offen.

Bedrohungsgrenze: Der Anker schützt gegen das Replay der dateibasierten
Sidecars durch einen Angreifer ohne Zugriff auf den Plattformstore. Er schützt
nicht gegen einen kompromittierten entsperrten Prozess, kompromittiertes OS,
autorisierten Keychain-/DPAPI-Zugriff oder vollständige physische
Plattformkompromittierung.

## ADR-081 - Kontrollierter ad-hoc-signierter Einzelpilot bleibt eigener Releasepfad

**Status:** Ergänzt ADR-070 und ADR-073 für Security Sprint 6; reine
Releasepfad-Dokumentation, kein Build und keine Veröffentlichung.

Die fehlende Developer-ID ist kein Blocker für den bereits eng kontrollierten
Laura-Einzelpiloten. Dieser Pfad verlangt einen reproduzierbaren Clean Build,
ad-hoc-Signatur, SHA-256-Prüfsummenmanifest, persönliche oder anderweitig
kontrollierte Übergabe, dokumentierte Gatekeeper-Freigabe sowie reale Prüfung
von Bundle-ID-, Update- und Keychain-Stabilität. Er behauptet weder Apple-
Notarisierung noch eine verifizierte Entwickleridentität und ist keine Freigabe
für automatische oder breite Verteilung.

Der spätere Distributionspfad bleibt davon getrennt. Developer ID, Hardened
Runtime, Notarisierung und Stapling oder eine ausdrücklich entschiedene
schulinterne Administration/MDM bleiben organisatorische Release-Gates für eine
breitere Vertrauenskette. Sie sind keine Voraussetzung für die isolierte
Verschlüsselungsarchitektur. Security Sprint 6 baut, ersetzt oder veröffentlicht
kein RC-, Pilot-, DMG-, ZIP-, Appcast- oder Updateartefakt.

## ADR-080 - HMAC-authentisiertes Migrationsjournal und reine Recovery-State-Machine

**Status:** Für Security Sprint 5 als isolierte Foundation und ausschließlich
für den synthetischen Migrationsprototyp freigegeben. Keine Startup-,
Produktmigrations-, Austausch-, Rollback- oder Löschfreigabe.

Das Journal ist eine einzelne streng kanonische JSON-Datei mit Version,
Migration-ID, technischem Datenkontext, Database-Key-ID/-Generation,
DMK-Key-ID/-Generation,
HMAC-Algorithmus/-KDF-Version, Rollenpfaden, Dateibeweisen, aktuellem Zustand,
sanitisierten Prüf- und Fehlercodes sowie vollständiger begrenzter
Transition-Historie. Ein eigener HKDF-Kontext
`jenaplan-kompetenzmanager/migration-journal-auth/v1` leitet aus dem DMK einen
nur flüchtigen 256-Bit-HMAC-Schlüssel ab. `HMAC-SHA-256` authentifiziert alle
Journalfelder. Der HMAC ist öffentlich; DMK, Journal-Key, Database-Key,
Wrapping-Key, Passwort, Recovery-/Support-Secrets, Schülerdaten, Inhalte und
SQL stehen niemals im Journal.

Geprüfte Variante A, gewählt: kanonisches JSON wird vollständig in eine neue
Datei im selben Verzeichnis geschrieben, geflusht, soweit unterstützt mit
Datei-`fsync` dauerhaft gemacht, per `os.replace` publiziert und auf POSIX mit
Verzeichnis-`fsync` abgeschlossen. Vorteil sind kleine Angriffsfläche, keine
SQLite-Sidecars, einfaches Fuzzing und genau eine atomare Einheit. Nachteile
sind vollständiges Neuschreiben und die notwendige DMK-Verfügbarkeit für jede
Prüfung. Wartungs- und Testaufwand sind moderat; Recovery liest genau eine
authentisierte Einheit.

Geprüfte Variante B: ein eigenes STRICT-SQLite-Journal mit Events,
Transaktionen und HMAC je Datensatz. Vorteile wären starke
Transaktionssemantik und natürliche append-only Tabellen. Nachteile sind ein
zweiter SQLite-Lifecycle, Locking, eigene `-journal`-/Recoveryfälle,
Windows-Sharing-/Antivirusrisiken, größere Packagingfläche und deutlich mehr
Tests. Für höchstens einige Dutzend Zustandswechsel entsteht kein ausreichender
Produktvorteil. Ein unkeyed Hash oder eine unkeyed Hashkette wurde verworfen:
ein Angreifer mit Schreibzugriff könnte sie neu berechnen.

Die explizite Zustandsmaschine kennt `not_started`, Preflight, Quellenprüfung,
Backup-Start/-Erzeugung/-Prüfung, Zielerzeugung, Export, Validierung,
Neuöffnung, die nur vorbereiteten Swap-Zustände, Rollback, `failed`, `blocked`
und `completed`. Jede Kante ist allowlisted und exhaustiv getestet;
`completed`, `failed` und `blocked` sind terminal. Kritische Operationen haben
Write-ahead- und Abschlusszustand. Der Sprint-5-Prototyp darf nach
`reopen_verified` direkt `completed` erreichen; er führt keinen Swap aus.
Reservierte Prüf-Codes besitzen eine feste früheste Abschlussphase und dürfen
weder vorzeitig noch als unbekannte freie Werte eingetragen werden.
Journalzeitpunkte müssen monoton sein.

Journal und Envelope werden nach erfolgreicher HMAC-/AEAD-Prüfung zusätzlich
über Database-Context sowie Database-Key-ID und -Generation kreuzgebunden; ein
für denselben DMK gültiges, aber zu einer anderen Datenbank gehörendes Paar
blockiert. Dateipfade im Journal sind ausschließlich sichere Dateinamen unter einem vom
Aufrufer injizierten, symlinkfreien Test-Workspace. Quelle, Backup und Ziel
werden über denselben `O_NOFOLLOW`-Descriptor gehasht und durch Rolle,
`st_dev`, `st_ino`, Größe, SHA-256 und schwaches `mtime_ns` gebunden. Während
`target_created` und `export_started` darf sich nur der Inhalt des bereits identitätsgebundenen
Ziels ändern. Eine fehlende, zusätzliche, ausgetauschte oder hashabweichende
Datei blockiert. Keine Recovery-Entscheidung löscht oder ersetzt eine Datei.

Die reine Recovery-Auswertung liefert abhängig vom authentisierten Journal und
den erneut geprüften Dateien ausschließlich `no_action`, `verify_backup`,
`rollback_target`, `continue_validation`, `reopen_target`,
`cleanup_completed_artifacts` oder
`block_manual_review`. Unbekannte Version, falscher HMAC-Key, Temp-Rest,
illegale Historie, Widerspruch oder fehlender Beweis führen zu
`block_manual_review`. Mehrfacher Aufruf ist ohne Dateiveränderung identisch.
Die vorbereiteten Swap-Zustände blockieren in Version 1 immer, weil das Journal
noch keine beweisbare Rename-/Live-Pfad-Topologie besitzt. Bei
`rollback_started` wird ausschließlich zwischen dem identisch gebundenen noch
vorhandenen Ziel (`rollback_target`) und seinem Fehlen nach bereits erfolgter
Löschung (`no_action`) unterschieden; die unveränderte Quelle wird nicht
"restored".

Bedrohungsgrenze: HMAC erkennt Manipulation ohne DMK, aber nicht das gemeinsame
Zurückspielen einer vollständigen älteren, damals gültigen Journaldatei. Ein
produktiver Rollout benötigt dafür einen vertrauenswürdig monotonen Anker.
Ebenso schützt die Foundation nicht gegen einen kompromittierten Prozess mit
DMK-Zugriff oder gegen physische Datenträgeranalyse.

Auf macOS/POSIX gelten im isolierten Pfad `0700`/`0600`, `O_NOFOLLOW` und
Verzeichnis-`fsync`. Das belegt keine vollständige Stromausfallsicherheit;
`F_FULLFSYNC` bleibt zu bewerten. Die Prototyp-Löschung prüft die Datei-ID vor
`unlink`, kann aber ohne exklusiven Prozess-Lock oder handlegebundene
Plattformoperation einen Austausch exakt zwischen Prüfung und Löschung nicht
atomar ausschließen; der isolierte `0700`-Root reduziert nur die Angriffsfläche.
Diese historische ADR-080-Aussage beschreibt die Sprint-4/5-Engine und ist
keine Erlaubnis für die ausführende Sprint-6-Recovery. ADR-083 verbietet dort
pathname-basiertes `unlink`/`remove` und behält die evidence-gebundenen
Artefakte in retained Quarantine. Windows bleibt gesperrt, bis ACLs,
Reparse-Point-/Junction-Abweisung, handlebasierte Volume-/File-ID,
Replace-/Sharing-Verhalten und reale Crash-/Packagingtests implementiert sind.

## ADR-079 - Versioniertes AEAD-Format und atomare Product-Envelope-Registry

**Status:** Für Security Sprint 5 als isolierte Foundation freigegeben; keine
produktive Persistenzadresse, RuntimePaths-, Startup- oder Rotationsfreigabe.

`DatabaseKeyEnvelope` ist bewusst ein neuer Typ und überlädt den generischen
Sprint-2-`KeyEnvelope` nicht. Version 1 enthält exakt: Envelope-Version,
Database-Key-ID/-Generation, monotone Rewrap-Revision, festen Key-Purpose, Lifecycle-Status,
Wrapping-Algorithmus, KDF-Algorithmus/-Version, DMK-Key-ID/-Generation,
technische Database-Context-UUID, 96-Bit-Nonce, kanonischen UTC-Zeitpunkt und
Ciphertext. Der geschützte Inhalt sind exakt 32 zufällige Database-Key-Bytes;
AES-GCM publiziert 48 Byte einschließlich 128-Bit-Tag.

Alle öffentlichen Headerfelder einschließlich Nonce und Status bilden eine
einzige kanonische JSON-AAD. Unbekannte oder boolesch mehrdeutige Versionen,
Algorithmen, KDFs, Felder, Typen, Base64url-Darstellungen, Längen und Status
werden vor Entschlüsselung abgelehnt. Falscher DMK, falsche Bindung sowie
Manipulation von AAD, Nonce oder Ciphertext liefern nur sanitierte Fehlercodes.
Es gibt keinen Klartextfallback und keine Neuerzeugung bei Fehlern.

Geprüfte Variante A, gewählt: AES-256-GCM aus `cryptography` 49.0.0 mit pro
Versiegelung neuer zufälliger 96-Bit-Nonce. Vorteile sind etablierte AEAD-API,
explizite AAD, bestehende Buildabhängigkeit und breite macOS-/Windows-
Verfügbarkeit. Hauptrisiko ist Nonce-Wiederverwendung; jede Statusänderung
erhöht deshalb die authentifizierte `rewrap_revision`, die Bestandteil des
HKDF-Kontexts ist, und verwendet zusätzlich eine neue Zufallsnonce. Selbst eine
nicht benachbarte Zufallsnonce-Kollision trifft damit einen anderen AEAD-Key;
gleiche aufeinanderfolgende Nonces werden zusätzlich abgewiesen. Der persistente
Registry-High-Water-Mark verhindert Generationswiedervergabe nach terminaler
Metadatenbereinigung.

Geprüfte Variante B: ChaCha20-Poly1305 mit KBKDF-HMAC-SHA-256. Vorteile wären
explizite Label-/Context-Trennung und gute Softwareleistung ohne
AES-Beschleunigung. Nachteile sind dieselbe Nonce-Eindeutigkeitsanforderung,
eine neue KDF-Entscheidung, Abweichung von der bestehenden HKDF-Voranalyse und
zusätzliche Plattform-/Packagingtests ohne Nutzen für 32 Byte Nutzlast.
AES-GCM-SIV wurde wegen Nonce-Missbrauchsresistenz geprüft, aber wegen
OpenSSL-/Backendverfügbarkeit und zusätzlichem Produktbuild-Gate nicht gewählt.
RFC-3394 AES Key Wrap allein erfüllt die verbindliche AAD-/Nonce-Anforderung
nicht.

Die isolierte Registry `database-key-envelopes-v1.json` enthält zusätzlich die
stabile Database-Context-UUID und den monotonen Generations-High-Water-Mark und liegt als eigener
Sidecar weder in fachlicher SQLite noch in `security.sqlite`,
`data-keysets.sqlite`, Keychain oder Journal. Sie speichert nur bereits
geschützte Envelopes. Tempdatei, Flush, Datei-`fsync`, atomare Publikation und
POSIX-Verzeichnis-`fsync` schützen den letzten Zustand; `0600`/`0700`,
Symlinkabweisung, Descriptor-/Dateiidentitätsprüfung und Compare-before-replace
begrenzen Pfadaustausch. Vorhandene unbekannte, korrupte oder geänderte Dateien
werden nicht überschrieben; Temp-Reste blockieren.

Die gesamte kanonische Registry einschließlich Version, Context,
High-Water-Mark und Envelope-Mitgliedschaft wird zusätzlich mit HMAC-SHA-256
authentifiziert. Der ausschließlich flüchtige MAC-Key stammt aus der getrennten
HKDF-Domain `jenaplan-kompetenzmanager/database-key-registry-auth/v1` und ist
an die Database-Context-UUID gebunden. Damit werden auch eine leere Registry,
selektives Entfernen/Wiedereinsetzen einzelner Envelopes und Steuerdaten-
Manipulation ohne DMK erkannt. Vollständiges Replay einer früher gültigen
Registry bleibt ohne externen monotonen Anker das dokumentierte Release-Gate.

Lifecycle: `create pending`, `activate`, idempotentes `load active`, `revoke`,
`fail`, Generations- und Mehrfach-Aktiv-Prüfung sowie explizite idempotente
Metadatenlöschung terminaler Einträge; Context und High-Water-Mark bleiben dabei
erhalten. Jede Statusänderung authentifiziert den neuen Status mit neuer
Rewrap-Revision und Nonce. Produktive Rotation und physisch sicheres Löschen
auf APFS/NTFS/SSD sind nicht implementiert oder behauptet.

## ADR-078 - Domain-separierte Product Database-Key-Hierarchie

**Status:** Für Security Sprint 5 als isolierte kryptografische Foundation
freigegeben; keine Aktivierung der Datenbankverschlüsselung.

Die verbindliche Hierarchie wird implementiert als `zufälliger 256-Bit-DMK ->
zweckgebundener 256-Bit-Database-Wrapping-Key -> zufälliger 256-Bit-
Database-Key -> SQLCipher`. App-Passwort, Recovery-Code, Support-Key und
Gerätecredential sind an keiner Ableitung beteiligt. Der Database-Key wird mit
`secrets.token_bytes` erzeugt und nie deterministisch aus Pfad,
Installations-ID, Passwort oder DMK abgeleitet.

Gewählt ist HKDF-SHA-256 aus `cryptography` mit dokumentiertem festem
Extract-Salt und einer kanonischen `info`, die Zweck, Ableitungsversion,
DMK-Key-ID/-Generation, Database-Context-UUID, Database-Key-Generation und
Rewrap-Revision
enthält. Der feste Zweck lautet
`jenaplan-kompetenzmanager/database-key-wrap/v1`. Gleicher DMK und identischer
vollständiger Kontext liefern denselben flüchtigen Wrapping-Key; anderer Zweck,
Version, DMK-Kontext, Datenbankkontext, Generation oder Rewrap-Revision liefert
einen anderen Schlüssel.
Der Wrapping-Key wird nicht persistiert und nicht für Dokumente oder Backups
verwendet. Registry-HMAC und Journal erhalten jeweils eigene getrennte Zwecke.

Geprüfte Variante A, gewählt: HKDF-SHA-256 plus AES-256-GCM. Vorteile sind der
für hochentropische Eingabeschlüssel passende Extract-and-Expand-Vertrag,
kleine API, etablierte Library und klare Erweiterbarkeit durch neue
versionierte Zwecke. Nachteile sind unvermeidliche Secret-Kopien in Python/
OpenSSL und die Notwendigkeit strikt stabiler Kontextkodierung. Wartungs- und
Testaufwand sind moderat; Re-Wrapping kann später vom SQLCipher-Datenwechsel
getrennt werden.

Geprüfte Variante B: unmittelbares Wrapping jedes Database-Key durch
macOS-Keychain beziehungsweise Windows-DPAPI. Vorteil wäre weniger eigene
KDF-Metadaten. Nachteile sind Umgehung der beschlossenen DMK-/Keyset-Domain,
plattformverschiedene Envelopes, schwierigere Recovery/Rotation und stärkere
Gerätebindung. KBKDF-HMAC-SHA-256 wäre kryptografisch tragfähig, hat gegenüber
HKDF im vorhandenen Architekturpfad aber keinen Integrationsvorteil.

Die Database-Context-UUID ist eine technische, authentifizierte Bindung und
kein Pfad oder fachlicher Identifier. Eine zusätzliche Installationsbindung
wird in Sprint 5 bewusst nicht gesetzt, weil sie Restore und Gerätewechsel
vorweg entscheiden würde. Ein späterer produktiver Datenbankanker muss diese
UUID innerhalb der verschlüsselten Datenbank oder eines vertrauenswürdigen
monotonen Metadatenmodells binden.

Verbleibende Grenzen: Python kann immutable Secret-Kopien und native
Bibliothekspuffer nicht garantiert löschen. Der Registry-High-Water-Mark ist
kein gegen Rollback geschützter externer monotoner Anker; gemeinsames
Zurückspielen einer älteren gültigen Registry bleibt daher möglich. Der
Windows-DMK-Store ist weiterhin nicht implementiert. Reale Keychain-,
DPAPI-, SQLCipher-, PyInstaller-, Signatur-, Update- und Crashabnahmen bleiben
Release-Gates.

## ADR-077 - Separater synthetischer SQLCipher-Migrationsprototyp und DB-Key-Hierarchie

**Status:** Für Security Sprint 4 ausschließlich als isolierter Prototyp mit
synthetischen Daten freigegeben; keine Produkt-, Startup-, Austausch-,
Backup/Restore-, Pilot- oder Releasefreigabe.

Die vorgeschlagene Hierarchie wird mit einer zusätzlichen Zwecktrennung
übernommen: Ein zufälliger 256-Bit-Database-Key verschlüsselt genau eine
fachliche SQLCipher-Datenbank. Der DMK wird nicht als SQLCipher-Key verwendet,
sondern leitet später per domain-separiertem KDF-Kontext einen flüchtigen
Database-Wrapping-Key ab. Dieser schützt den zufälligen Database-Key in einem
authentisierten, versionierten Envelope. Dokument-, Backup- und spätere Keys
erhalten eigene Zwecke und dürfen weder Database-Key noch Wrapping-Key
wiederverwenden. Security Sprint 4 implementiert davon nur einen zufälligen
flüchtigen Test-Database-Key; DMK-Ableitung, Envelope, Store und Rotation
bleiben gesperrt.

Diese Trennung ist besser als `DMK == SQLCipher-Key`, weil DMK-Wechsel ein
reines Re-Wrapping erlauben können, Datenbankkeyrotation getrennt planbar ist
und die Kompromittierung eines Verwendungszwecks nicht automatisch alle
anderen Schlüsselzwecke öffnet. Ein deterministisch direkt aus dem DMK
abgeleiteter Database-Key wurde wegen enger Rotations-, Wiederherstellungs- und
Mehrdatenbankkopplung verworfen. Ein passwortabgeleiteter SQLCipher-Key wurde
wegen Passwortwechsel, Offline-Brute-Force und Vermischung von Anmeldung und
Datenverschlüsselung verworfen. Direktes Plattform-Wrapping jedes Inhaltskeys
bleibt technisch möglich, würde aber die bereits gewählte DMK-/Keyset-Domain
umgehen.

Der Prototyp öffnet die durch Application-ID, User-Version und Guard-Tabelle
dreifach markierte Quelle ausschließlich read-only/immutable. Er erstellt ein
separates verifiziertes SQLite-Backup und ein neues Cipher-Ziel. Der Transfer
verwendet die offizielle `sqlcipher_export('main', 'plaintext')`-Semantik. Weil
`sqlcipher_export` `user_version` und `auto_vacuum` nicht übernimmt, setzt der
Prototyp `auto_vacuum` vor dem Export sowie `application_id` und `user_version`
innerhalb der Exporttransaktion explizit. Es gibt keinen In-place-`rekey` und
keinen SQLite-Fallback.

Freigabe verlangt Gleichheit von Tabellen, Zeilenzahlen, Primärschlüsseln,
Fremdschlüsseldefinitionen, Triggern, Views, expliziten Indizes, persistenten
PRAGMAs, `sqlite_sequence`, normalisiertem Schemahash und typ-/längenkanonischen
Datenhashes pro Tabelle und global. Zusätzlich müssen `foreign_key_check`, `integrity_check`,
`cipher_integrity_check` und ein neues SQLCipher-Öffnen erfolgreich sein. Die
Quelle muss vor und nach dem Lauf denselben Datei-SHA-256 besitzen.

Rollback bedeutet in diesem Sprint: Die Quelle bleibt immer maßgeblich und
wird nie umbenannt. Ein fehlerhaftes eigenes Cipher-Ziel wird nur bei gleicher
Dateiidentität entfernt; ein bereits verifiziertes Backup bleibt erhalten. Ein
späterer atomarer Austausch braucht exklusiven Prozess-/Dateilock, dauerhaftes
Journal, `fsync` von Kandidat und Verzeichnis, retained rollback name,
atomaren Rename, erneutes Verzeichnis-`fsync`, SQLCipher-Neuöffnen und eine
eindeutige Start-Recovery-State-Machine. Dieser Austausch wird nur beschrieben,
nicht ausgeführt.

RC `0.2.2`, normale `sqlite3`-Runtime, `security.sqlite`, Produkt- und
Pilotdaten, Dokumente, Backups, bekannte Excel-Datei, Startup, Login, Recovery,
Touch ID, Support Reset, Appcast und Releaseartefakte bleiben unverändert.

## ADR-076 - SQLCipher als explizite isolierte Datenbank-Engine

**Status:** Für Security Sprint 3 als isolierte optionale Infrastruktur
freigegeben; keine Produkt-, Startup-, Migrations-, Backup-, Restore-, Pilot-
oder Releasefreigabe.

Die Anwendung behält Standard-`sqlite3` als feste Default-Engine. Eine kleine
Qt-freie Provider-Grenze kapselt treiberspezifische Connection-Erzeugung,
Row-Factory, PRAGMAs, Versions- und Integritätsprüfungen. SQLCipher ist nur
durch explizite Konstruktion erreichbar. Es gibt weder Umgebungsumschaltung
noch stillen Fallback. Die normale fachliche Verbindung delegiert bei
funktional unverändertem Verhalten an den Standard-SQLite-Provider.
SQLCipher-Aktivierung, Security Store, Development-Keyset-Sidecar, Backup,
Restore und Startup-Konfiguration bleiben außerhalb dieser Naht.

Als DB-API wird `sqlcipher3` gewählt, weil es dem bestehenden `sqlite3`-Modell
am nächsten liegt. Der isolierte macOS-arm64-/Python-3.14-Spike pinnt
`sqlcipher3` 0.6.2 und prüft die tatsächlich geladene SQLCipher Community
Engine exakt als `4.12.0 community`. Dieses öffentliche Wheel ist keine
Produktfreigabe: Es wurde nicht über Trusted Publishing veröffentlicht, nennt
die eingebettete SQLCipher-Version nicht in den Paketmetadaten und liegt hinter
dem Produktziel SQLCipher 4.17.0. Für eine spätere Freigabe sind kontrolliert
aus geprüften Quellen gebaute, hash-gepinnte Wheels gegen exakt SQLCipher
4.17.0 für macOS arm64 und Windows x64 erforderlich.

Die macOS-arm64-Seite dieses Buildgates ist nun als getrennte, nicht
produktaktivierte Basis belegt. Der Build erzeugt aus SQLCipher-Tag `v4.17.0`
(Commit `810db22f575ee7cf94ea96a3e91622b5fcece3dc`) und `sqlcipher3` 0.6.2
(Commit `14fc2632676b20011e0bba64fdda49763a2dd2ec`) eine lokal eindeutig
markierte Binding-Version. `SQLCIPHER_CRYPTO_CC`, Security.framework und
CoreFoundation ersetzen den unkontrollierten Conan-/OpenSSL-Pfad. Python,
SDK, Compiler, Buildwerkzeuge, Quellen, Amalgamation, temporärer Bindingpatch,
Lizenztexte und Wheel sind hash- beziehungsweise versionsgebunden. Zwei
unabhängige Buildroots erzeugten dasselbe arm64-Wheel; Runtime und Linkage
wurden in einem dritten Venv geprüft. Daraus folgt weder eine Windows-,
Produkt-, Startup-, Migrations-, Packaging- noch Releasefreigabe.

Geprüfte Alternativen: Ein kontrollierter `sqlcipher3`-Source-Build gegen
4.17.0 ist das spätere Ziel, benötigt aber eigene Wheel-/SBOM-/CVE-Pflege.
APSW plus eigener SQLCipher-Build ist technisch möglich, wegen abweichender
Row-, Exception-, Transaktions- und Backup-Semantik für den kleinen Sprint aber
zu invasiv. `pysqlcipher3` wird wegen eingestellter Wartung, altem SQLCipher-
Stand, fehlenden modernen Wheels und externer nativer Buildabhängigkeit
abgelehnt. Offizielle kommerzielle SQLCipher-Pakete bleiben eine
Beschaffungsoption, stellen aber kein öffentliches offizielles Python-DB-API
bereit.

Der Provider akzeptiert im Sprint ausschließlich einen expliziten, zur
Laufzeit erzeugten 32-Byte-Testkey. App-Passwort und DMK sind ausgeschlossen.
Später ist ein eigener zufälliger DB-Key unter einem zweckgebundenen
DMK-Wrapping erforderlich; Ableitung, Wrapping und Persistenz sind nicht Teil
dieser Entscheidung. Der rohe Key wird als erste SQLCipher-Operation gesetzt,
aus `repr`, Logs und Fehlern ferngehalten und in einem kopierten Python-
`bytearray` bestmöglich überschrieben; das Binding-Statement-Caching ist
deaktiviert. Die unvermeidbare immutable Hex-/SQL-Zeichenkette sowie Python
und der C-Treiber garantieren dennoch keine vollständige sofortige
Speicherlöschung.

Nach dem Keying und vor dem ersten Schema-Lesezugriff werden Cipher-Version,
`cipher_status`, `cipher_plaintext_header_size=0`, 4096-Byte-Cipherseiten,
256000 KDF-Iterationen, HMAC-SHA-512, PBKDF2-HMAC-SHA-512, Seiten-HMAC,
Memory-Security und In-Memory-Tempstore gesetzt und geprüft. Danach folgen
DELETE-Journal, FULL-Synchronisierung, Secure Delete und Foreign Keys.
Jedes Öffnen verlangt Schemaauthentisierung, `cipher_integrity_check`,
`integrity_check` und `foreign_key_check`. Klartext-SQLite, fehlende Engine,
falsche Version, fehlende/ungültige Keys und beschädigte Dateien werden ohne
Neuerstellung abgewiesen. Falscher Schlüssel, beschädigter verschlüsselter
Header und inkompatible Cipher-Parameter können denselben `SQLITE_NOTADB`-
Befund erzeugen; die gemeinsame sanitierte Ablehnung ist beabsichtigt und
vermeidet eine nicht belegbare Fehlerursache.

SQLCipher Community verlangt BSD-artige Attribution und zugängliche
Lizenzhinweise einschließlich der Abhängigkeiten. Beim Binding widersprechen
sich PyPI-Metadaten (`MIT`) und mitgelieferte Lizenzdatei/Repository
(zlib-artig); vor Distribution muss der tatsächlich gebaute Quell- und
Notice-Satz geklärt werden. Ein isolierter arm64-PyInstaller-Onefile-Smoke
funktioniert und enthält sowohl Standard-`sqlite3` als auch die statisch
eingebettete SQLCipher-Extension. Wegen des späten Imports muss die spätere
PyInstaller-Spec Binding, Extension und Lizenzdaten explizit sammeln; ohne
diese Regel fehlt SQLCipher und der Provider bricht fail-closed ab. Developer-ID, Hardened Runtime,
Notarisierung, DMG, Update-ZIP, saubere Bundle-Notices, reproduzierbarer Build,
Windows x64, Authenticode und echter Upgradepfad bleiben Release-Gates.

## ADR-075 - Isolierte Key Foundation mit plattformgeschütztem Data Master Key

**Status:** Für Security Sprint 2 als isolierte Entwicklungsgrundlage
freigegeben; keine Produkt-, Startup-, Migrations- oder Releasefreigabe.

Der DMK besteht aus genau 32 zufälligen Bytes und ist unabhängig vom
App-Passwort. Domain und Application Layer besitzen den Lifecycle; ein
plattformneutraler Port besitzt die Secret-Persistenz. macOS verwendet den
eigenen, nicht synchronisierenden Keychain-Service
`de.jenaplan.kompetenzmanager.data-master-key`. Der Gerätecredential-Namespace
wird nicht wiederverwendet. Für Windows ist ausschließlich der gemeinsame Port
für eine spätere DPAPI-/Credential-Manager-Implementierung definiert.

Versionierte Keysets durchlaufen `pending`, `active`, `revoked` oder `failed`.
Der isolierte Entwicklungs-Sidecar speichert ausschließlich Key-ID,
Generation, Status und SHA-256-Fingerprint. DMK und geschütztes
Envelope-Material werden niemals in SQLite gespeichert. Das versionierte
Envelope-Format transportiert ausschließlich bereits plattformgeschütztes
Material mit Key-ID, Zweck, Algorithmus und technischen Metadaten; es führt
selbst keine Verschlüsselung aus.

Länge und Fingerprint werden bei jedem Laden geprüft. Fehlende oder beschädigte
aktive Einträge schlagen fail-closed fehl und werden niemals still ersetzt;
der noch nicht authentifizierte Development-Sidecar darf bei einer
uneindeutigen Längen-/Fingerprintabweichung den möglicherweise korrekten
Plattform-DMK nicht automatisch löschen. Temporäre Zugriffs- und
Plattformfehler bleiben wiederholbar. Widerruf wird vor
der Plattformlöschung festgeschrieben. Ein Löschfehler kann über die terminalen
Metadaten erneut bereinigt werden. Passwortwechsel, Recovery und Support-Reset
rotieren oder verändern den DMK in diesem Sprint nicht.

Der bestehende RC `0.2.2`, `security.sqlite`, Pilotdaten, fachliche SQLite,
Dokumente, Backups, SQLCipher und App-Start bleiben vollständig außerhalb
dieser Entscheidung. Eine spätere Produktintegration benötigt einen eigenen
Product-Owner-, Datenmodell-, Migrations-, Packaging- und Releaseentscheid.

## ADR-074 - Separater grafischer Support-Assistent

**Status:** Für Sprint 0.2S.1 freigegeben.

Der Betreiberworkflow wird als eigene PySide-Anwendung mit eigener Bundle-ID
und eigenem Supportpaket umgesetzt. Er wird nicht in Haupt-App, Pilot-/Laura-
Pakete oder normalen Updatekanal integriert. Die Qt-freie Application-Schicht
verwendet ausschließlich den bestehenden Requestcodec und Tokengenerator;
Widgets besitzen weder Protokoll-, Krypto- noch Dateipersistenzlogik.

Der vorhandene Terminalweg bleibt als technisch validierter Referenz- und
Fallbackpfad erhalten. Der Support-Assistent ändert weder Request- noch
Tokenformat. Weil Format 1 keinen Gerätenamen oder Benutzernamen enthält, wird
der Installationsname nur flüchtig erfasst und der Benutzername ehrlich als
nicht enthalten projiziert. Eine Protokollerweiterung würde eine eigene
Security- und Kompatibilitätsentscheidung benötigen und ist ausgeschlossen.

Der private Schlüssel bleibt extern. Das Bundle enthält ausschließlich die
öffentliche Produktregistry und prüft den bewusst gewählten verschlüsselten
Ed25519-Schlüssel dagegen. Audit ist eine eigene minimale JSONL-Quelle des
Support-Assistenten mit genau Zeitpunkt, Request-ID, Key-ID und Aktion.

## ADR-073 - Sparkle 2 als sicherer macOS-Updatepfad ab Version 0.2.1

**Status:** Architektur für Sprint 0.2U.1 entschieden; ein isolierter
Implementierungssprint darf beginnen, produktive Auslieferung bleibt an die
unten genannten Release-Gates gebunden.

### Verifizierte Ausgangslage und Spike

Der aktuelle Buildvertrag erzeugt ein PyInstaller-App-Bundle mit Bundle-ID
`de.jenaplan.kompetenzmanager`, Version/Build `0.2.0`, Mindestversion macOS 13
und Zielarchitektur arm64. Es gibt keine App-Sandbox- oder Updateentitlements.
Lokal ist keine Developer-ID-Identität vorhanden; der vorhandene Buildpfad
signiert deshalb ad hoc, ohne Notarisierung und ohne belastbare
Update-Vertrauenskette.

Der ausschließlich außerhalb des Produktrepositorys ausgeführte Spike nutzte
die offizielle Sparkle-Distribution `2.9.4` (`Sparkle-2.9.4.tar.xz`,
SHA-256 `ce89daf967db1e1893ed3ebd67575ed82d3902563e3191ca92aaec9164fbdef9`).
Framework und Helfer enthalten arm64; eine minimale Objective-C-/C-ABI-Bridge
ließ sich für macOS 13 arm64 linken, aus einem PySide-Prozess laden und in eine
isolierte Kopie des Bundles einbetten. Codesign-Verifikation, der vorhandene
Packaged-Smoke und der Scan auf eingebettete SQLite-/DB-Dateien blieben dort
erfolgreich. Das bestätigt technische Machbarkeit, nicht produktive Signierung,
Notarisierung, Feedbetrieb oder Schlüsselverwaltung. Die Implementierung muss
Version und Hash erneut reviewen und exakt pinnen.

### Entscheidung und Versionsübergang

Der native macOS-Updatepfad verwendet Sparkle 2. Die PySide-Anwendung bindet
das Framework über eine kleine Objective-C++-/C-ABI-Bridge in der
Infrastructure-Schicht ein. Eine Qt-freie Application-Schnittstelle liefert
nur Updatezustand, Version, Kanal, Fortschritt und strukturierte Fehler; die
bestehende Einstellungsansicht projiziert diese Daten. Widgets laden weder
Feeds noch Dateien und entscheiden weder Signaturen noch Installation.

`0.2.0` bleibt unverändert und wurde Laura noch nicht installiert. Ihre erste
tatsächliche Installation ist deshalb direkt `0.2.1` aus einem bewusst manuell
geöffneten DMG. Ein inhaltlich anderes `0.2.0` wird nicht neu gebaut, weil es
dieselbe sichtbare und technische Version tragen und keinen verlässlichen
Updateausgangspunkt bilden würde. Ab `0.2.1` steht Sparkle im beaufsichtigten
Pilotbetrieb nur auf ausdrückliches `Nach Updates suchen` bereit;
automatische Prüfungen, automatische Downloads und automatische Installation
bleiben aus. Ein produktiver automatischer Installationsmodus ist nicht Teil
dieser Entscheidung.

`CFBundleShortVersionString` folgt SemVer (`0.2.1`). `CFBundleVersion` wird als
eigene monoton steigende Buildnummer geführt; Appcast, Bundle, Build-Info,
DMG, Prüfsummen und Release-Inventar müssen dieselben beiden Werte nennen. Ein
Appcast-Eintrag muss strikt neuer sein und `macOS >= 13` sowie `arm64` verlangen.

### Vertrauenskette, Kanäle und Packaging

Für reguläre Verteilung verlangt jedes Release dieselbe stabile Bundle-ID, eine gültige Developer-ID-
Application-Signatur mit Hardened Runtime und sicherem Zeitstempel, vollständige
Signierung aller verschachtelten Sparkle-Helfer und Frameworks, erfolgreiche
Apple-Notarisierung, geprüftes Notary-Log und an App sowie DMG geheftete Tickets.
Eine pauschale produktive `codesign --deep`-Nachsignierung ist ausgeschlossen;
verschachtelte Komponenten werden innen nach außen mit ihrer vorgesehenen
Identität signiert und anschließend strikt verifiziert.

Artefakt und Appcast sind unabhängig authentisiert: ausschließlich HTTPS,
Sparkle-EdDSA-Signatur des unveränderten DMG/Archivs, signierter Feed und
Verifikation vor dem Entpacken. Nur der öffentliche EdDSA-Schlüssel liegt im
Bundle. Privater Schlüssel, Feed-Signierschlüssel, Developer-ID-Privatschlüssel,
Notarisierungszugänge und Passwörter bleiben außerhalb von Repository, App,
DMG, Logs und Supportpaket. Schlüsselrotation darf nie Apple-Signieridentität
und Sparkle-EdDSA-Schlüssel im selben Übergangsrelease wechseln.

Pilot und Stable verwenden zwei feste, nicht durch Lehrkräfte editierbare
HTTPS-Appcast-URLs. Der Pilotfeed enthält ausschließlich freigegebene
Pilotartefakte und den Kanal `pilot`; der spätere Stable-Feed ausschließlich
den Defaultkanal. Eine Pilotversion wechselt nicht automatisch auf Stable.
Der einzelne beaufsichtigte Laura-Pilot darf mit ad-hoc-signierten Bundles
erprobt werden. Diese Ausnahme ist weder Developer-ID-/Notarisierungsnachweis
noch Freigabe eines produktiven Updatekanals.
Feedveröffentlichung ist ein eigener, atomarer Release-Schritt: zuerst
Artefakt hochladen und unabhängig prüfen, zuletzt den vollständig signierten
Appcast veröffentlichen. Zurückziehen entfernt den Eintrag aus dem Feed, nicht
eine bereits installierte Version.

Das aktuelle Produkt ist nicht App-Sandboxed. Daher wird Sparkle zunächst ohne
separate Downloader-/Installer-XPC-Dienste integriert. App-Sandbox, XPC-
Mach-Lookup-Ausnahmen oder zusätzliche Netzwerkentitlements dürfen nicht
vorsorglich ergänzt werden; eine spätere Sandbox-Entscheidung öffnet diesen
Security-Review erneut.

### Daten-, Security- und Installationsgrenze

Sparkle ersetzt atomar nur `/Applications/Jenaplan-Kompetenzmanager.app`.
`~/Library/Application Support/Jenaplan-Kompetenzmanager/` einschließlich
fachlicher SQLite, `documents/`, `exports/`, `backups/`, `logs/`,
`security/security.sqlite`, Enrollment-Marker und `app-preferences.json` wird
weder in den Feed aufgenommen noch kopiert, gelöscht oder zurückgesetzt. Der
macOS-Schlüsselbundeintrag unter dem stabilen Service bleibt ebenfalls
außerhalb des Updateartefakts. Das Update ist kein Backup und kein Restore.

Vor Download darf die App auf eine neue Version hinweisen. Installation und
Relaunch sind nur nach ausdrücklicher Zustimmung und an einem sicheren Punkt
zulässig: kein Backup/Restore/Support-Reset-Worker, kein Login-/Recovery-
Abschluss, kein laufender Schreibvorgang und kein geänderter Bericht-/LEG-
Entwurf oder anderer vom Shell-Vertrag gemeldeter ungespeicherter Arbeitsstand.
Kann die Shell diese Bedingungen nicht vollständig beweisen, wird die
Installation verschoben; sie darf die App nicht erzwungen beenden.

Der klassische Schlüsselbundvertrag aus ADR-068 vertraut der codesignierten
Anwendung. Ein ad-hoc neu signiertes Bundle erhält eine andere Codeidentität;
deshalb ist der Gerätecredential- und Touch-ID-Zugriff beim späteren Übergang
von der ad-hoc-signierten `0.2.1` auf einen Nachfolger nicht als erhalten
bewiesen. Dieser Übergang muss auf dem realen Pilot-Mac mit vorher aktiviertem
Gerätecredential geprüft werden. Passwort-Fallback muss immer funktionieren;
eine einmalige Neuanmeldung/Neuregistrierung ist im Einzelpilot akzeptabel,
Konto- oder Datenverlust nicht. Eine nur auf Bundle-ID basierende ad-hoc-
Vertrauensregel ist als spoofbar ausgeschlossen. Ab einem
erfolgreich geprüften Developer-ID-Basisstand müssen alle Updates dieselbe
designated requirement erhalten.

Security Store v3 besitzt kontrollierte interne Migrationen; die fachliche
Datenbank besitzt derzeit keinen allgemeinen Start-Migrations-/Rollbackvertrag.
Daher ändert `0.2.1` weder Fachschema noch Securityformat. Vor jedem späteren
schemaändernden Update sind Vorwärtsmigration, Wiederanlauf, Sicherungszeitpunkt,
Kompatibilitätsfenster und Rollback gesondert zu entscheiden und zu testen.
Bis dahin bedeutet Rollback ausschließlich: App schließen, vorheriges
Developer-ID-signiertes/notarisiertes DMG wieder installieren und dieselben
unveränderten Daten öffnen. Ein Downgrade nach Schemaänderung ist verboten.

### UX, Fehler und Freigabe

`Einstellungen -> Updates` zeigt installierte Version/Build, festen Kanal,
Zeitpunkt der letzten Prüfung und genau eine Primäraktion `Nach Updates suchen`.
Die Zustände lauten ruhig und lokalisiert: aktuell, Update verfügbar, Prüfung,
Download, bereit zur Installation, verschoben und fehlgeschlagen. Release Notes
dürfen aus dem authentisierten Feed angezeigt werden; Fehler nennen keine
lokalen Pfade, IDs, Tokens, Feedinhalte oder Schülerdaten. Offline, Timeout,
ungültiger Feed, ungültige Signatur, falsche Architektur/Systemversion,
Notarisierungs-/Installationsfehler und nicht beschreibbarer App-Ort bleiben
fail-closed und führen zum manuellen DMG-Hinweis, niemals zum Umgehen der
Prüfung.

Freigabegates sind: echte Developer-ID lokal verfügbar; reproduzierbare
Signierung innen nach außen; Hardened-Runtime-Test; Notarisierung und Stapling;
Sparkle-Version und Distributionshash gepinnt; HTTPS-Feed und Hostingbetrieb;
EdDSA-Schlüsselprozess/Rotation; Pilot-/Stable-Trennung; Feed- und
Artefaktsignatur-Negativtests; arm64/macOS-13-Bundleprüfung; Update von
installierter `0.2.1` auf einen Testnachfolger; Offline-/Abbruch-/Retry-
Verhalten; keine Daten im Bundle; unveränderte Fach-, Dokument-, Backup-,
Security- und Präferenzdaten; Keychain/Touch-ID-/Passwort-Fallback auf realer
Hardware; sicherer Installationsaufschub bei ungespeicherter oder laufender
Arbeit; manueller Rollback bei schemaidentischen Versionen. Ohne ein Gate gibt
es keinen produktiven Feed.

Technische Primärreferenzen sind die Sparkle-Dokumentation zu
[Integration](https://sparkle-project.org/documentation/),
[programmatischer Qt-Anbindung](https://sparkle-project.org/documentation/programmatic-setup/),
[Sandbox/XPC](https://sparkle-project.org/documentation/sandboxing/),
[Appcasts und Kanälen](https://sparkle-project.org/documentation/publishing/) und
[Sicherheitsmodell](https://sparkle-project.org/documentation/security-and-reliability/)
sowie Apples Vorgaben zu
[Developer ID](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/)
und
[Notarisierung/Hardened Runtime](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

## ADR-072 - Getrenntes Offline-Supportpaket und versionierte Produktivregistry

**Status:** Für Sprint 0.2B.6 freigegeben.

Der Supportbetrieb wird nicht in App, DMG oder Laura-Paket aufgenommen. Ein
separates macOS-arm64-Paket enthält ausschließlich zwei Finder-Starter,
eigenständige Offline-Laufzeiten, Betriebsanleitung, öffentliche
Registry-Struktur, Version und Prüfsummen. Die Starter bestimmen ihren eigenen
Ort, übertragen keine Secrets als Argument oder Umgebung und delegieren die
Passphraseeingabe ausschließlich an Python `getpass`.

Reset-Signatur und Schlüsselbereitstellung bleiben getrennte lineare Prozesse.
Private Ed25519-Schlüssel entstehen nur bewusst außerhalb jedes Repositorys,
direkt passphrasenverschlüsselt als PKCS#8. Der Signaturprozess prüft Anfrage,
Gerätebestätigung, Dateirechte, Schlüsselpaar und Fingerprint und publiziert nur
eine exklusiv neu angelegte kurzlebige Token-Datei. Er öffnet keine fachliche
SQLite, Backups oder Dokumente.

Die App lädt öffentliche Produktivschlüssel aus einem codeversionierten
Manifest der Formatversion 1. Manifest und Einträge werden vollständig und
deterministisch validiert. `active` sowie das kurze Rotationsfenster `retiring`
sind verifizierbar; `retired`, `revoked`, unbekannte, noch nicht gültige und
abgelaufene Schlüssel sind fail-closed. Aktivierung, Rotation und Widerruf
erfordern weiterhin einen App-Release. Ohne ausdrücklich bereitgestellten
öffentlichen PO-Schlüssel bleibt das Manifest leer; kein Testschlüssel wird zum
Produktivschlüssel umgedeutet.

## ADR-071 - Zentrale maximierte Arbeitsfenster und deterministische LEG-Seiten

**Status:** Für den UI-Stabilitätsnachschnitt von Version 0.2.0 freigegeben.

Beobachtungs-, Bericht- und LEG-Arbeitsfenster werden über eine gemeinsame
Qt-Window-Policy als maximierte normale Fenster auf dem Bildschirm des
Hauptfensters geöffnet. Die Policy verwendet ausschließlich die verfügbare
Bildschirmgeometrie, berücksichtigt damit Menüleiste und Dock, setzt keinen
macOS-Vollbildzustand und begrenzt vorhandene Mindestgrößen auf sehr kleinen
Displays. Fachlogik, Persistenz und Dialoginhalte bleiben davon getrennt.

Der LEG-Seitenwechsel verwendet weiterhin genau einen `QStackedWidget`-Eintrag
je vorhandener Phase. Nicht aktive Seiten werden zusätzlich unsichtbar und
nicht interaktiv gehalten. Ein Opazitätseffekt auf dem gesamten Stack ist
unzulässig, weil dessen Plattform-Rendering vorherige Seitenbilder cachen und
über die neue Seite zeichnen kann. Seiten und Eingaben bleiben im Widgetbaum,
sodass Vor-/Zurücknavigation keinen Entwurfszustand verwirft.

Lange Bestätigungsaktionen erhalten ihre Mindestbreite aus der finalen
Schriftmetrik zuzüglich Fokus- und Innenabstand. Die Primäraktion bleibt der
sichere Fortsetzungsweg; Enter und Escape dürfen weder Onboarding noch
ungespeicherte Berichtsinhalte unbeabsichtigt verwerfen.

## ADR-070 - Version 0.2.0 als leerer, ad-hoc-signierter Pilot-Release-Kandidat

**Status:** Für Sprint 0.2R freigegeben.

`src/version.py` bleibt die einzige Produktversionsquelle und verwendet das
vorhandene dreiteilige SemVer-Schema. Version `0.2.0` wird daraus in
Qt-Anwendung, PyInstaller-Metadaten, Build-Info, DMG und Dokumente übernommen.
Der finale Kandidat verwendet den Datenmodus `release`: Er enthält keine
Startdatenbank, Pilotdaten, Runtime-Dateien, AppPreferences, Security Stores,
Backups, Recovery- oder Reset-Artefakte.

Die Distribution besteht aus einem arm64-DMG, kanonisch gebauten PDFs,
Prüfsummen, Release-Inventar und einem auf diese freigegebenen Artefakte
begrenzten Laura-Paket. Die bestehende Test-Excel bleibt die einzige kanonische
Abnahmemappe. Build- und Übergabeartefakte sind keine neuen Governance- oder
Datenquellen.

Ohne verfügbare Developer-ID bleibt der Kandidat ad hoc signiert und nicht
notarisiert. Die produktive Support-Key-Registry bleibt leer. Reale Sleep/Wake-
und Touch-ID-Prüfung, App-Switcher, vollständige Aktivierungs-/Widerrufsreise,
produktiver Support-Reset, Developer-ID und Notarisierung sind keine
automatisiert bestandenen Release-Gates und bleiben sichtbar offen.

## ADR-069 - Sichtbarer Offline-Support-Reset als bestätigter Recovery-Handoff

**Status:** Für Sprint 0.2B.5 freigegeben.

Support-Reset ist kein Masterkennwort, keine Entschlüsselung und kein Zugriff des
Supports auf fachliche Daten. Die lokal erzeugte, versionierte Anfrage enthält
ausschließlich Installation, Nutzer, Anfrage-ID, Nonce, Aktion und technische
UTC-Zeitpunkte. Der extern erzeugte `JKM-SR1`-Token ist zusätzlich an `key_id`
und Ed25519 gebunden, kurzlebig und einmalig. Private Schlüssel und der
organisatorische Support-Audit bleiben vollständig außerhalb der App.

Die produktive `DEFAULT_SUPPORT_KEY_REGISTRY` bleibt leer, solange kein
öffentlicher Schlüssel ausdrücklich freigegeben ist. Die App darf trotzdem eine
technische Anfrage erzeugen, kopieren und bewusst als `.jkmresetrequest`
exportieren. Tokenprüfung und Reset bleiben mit unbekannter `key_id` fail-closed;
die UI nennt den fehlenden Produktivbetrieb ausdrücklich und verwendet keinen
Testschlüssel als Ersatz.

Der sichtbare Prozess trennt Tokenprüfung und irreversible Ausführung. Prüfung
liefert nur eine datensparsame Vorschau und konsumiert weder Anfrage noch Token.
Erst `Sicherheitsbackup erstellen und Passwort zurücksetzen` startet einen
nicht abbrechbaren Worker. Dieser verwendet den bestehenden Backup-Service,
publiziert und verifiziert ein normales fachliches `.jkmbackup` und übergibt den
Proof an den bestehenden Support-Reset-Core. Erst danach setzt eine einzelne
Security-Transaktion Konto, Recovery, Epoch und Gerätecredentials zurück.

Der Vor-Auth-Recoverypfad darf für genau dieses verpflichtende Sicherheitsbackup
die vorhandene fachliche SQLite und verwalteten Dokumente ausschließlich über
den Backup-Service lesen. Er baut keine AppShell, Adapter oder Fachprojektion auf
und verändert keine Fachdaten. Nach erfolgreichem Security-Commit werden alle
fachlichen Fenster verdeckt, die Sitzung verworfen, Keychain-Reste best effort
bereinigt und die App beendet. Der nächste Start verwendet ausschließlich den
bestehenden `password_reset_pending`-Abschluss mit neuem Passwort, neuem
Recovery-Satz und Sicherungsbestätigung.

Backup-/Restoreformat, fachliche IDs, Dokumentpfade, AppPreferences-Anzeigename
und Onboardingstatus bleiben unverändert. Die offenen physischen Pilot-Mac-
Prüfungen aus 0.2B.4/0.2B.4a bleiben offen.

## ADR-068 - Gerätecredential statt gespeichertem Passwort und optionale lokale Authentifizierung

**Status:** Für Sprint 0.2B.4a freigegeben.

`Auf diesem Gerät angemeldet bleiben` speichert keine Sitzung und kein
App-Passwort. Nach einer unmittelbar erfolgreichen Passwortanmeldung und
ausdrücklicher Zustimmung erzeugt der Security Application Service genau ein
zufälliges Gerätegeheimnis mit 256 Bit Entropie. Nur dieses Geheimnis liegt als
nicht synchronisierender generischer Passwortdatensatz im lokalen macOS-
Schlüsselbund. Eine explizite ACL vertraut ausschließlich der erzeugenden,
codesignierten Anwendung; der Accountname bindet Installation und Credential.
Der getrennte
Security Store speichert ausschließlich `credential_id`, Installation, Nutzer,
technisches datensparsames Label, individuellen Salt, versionierten
`SHA-256(salt || secret)`-Verifikationswert, Security-Epoch bei Ausstellung und
Status-/Zeitmetadaten. AppPreferences enthält keinen dieser Werte.

Eine gültige Geräteanmeldung darf am normalen Auth-Gate eine neue flüchtige
In-Memory-Sitzung erzeugen. Sie deaktiviert weder die manuelle noch die
Inaktivitäts- oder Wake-Sperre. Nach App-Ende existiert keine Sitzung. Fehlender
Schlüsselbundeintrag, falscher Verifikationswert, Epoch-Abweichung, widerrufener
Datensatz, Storefehler oder Plattformfehler führen ausschließlich zum
Passwort-Fallback; es gibt keinen stillen Wiederaufbau.

Die Qt-freie Anwendung definiert `DeviceCredentialRepository`,
`DeviceSecretStore` und `LocalDeviceAuthenticator`. macOS implementiert den
Secret Store über Security.framework und lokale Authentifizierung über
LocalAuthentication.framework; Widgets kennen weder Schlüsselbund noch
Biometrie. Andere Plattformen liefern einen strukturierten `unsupported`-Status
und behalten den vollständigen Passwortpfad. Windows Hello und Credential
Locker bleiben späteren Adaptern vorbehalten.

Touch ID ist optional und wird nur bei verfügbarer, eingerichteter Biometrie,
aktivem Credential, vorhandenem Geheimnis und passender Epoch angeboten. Eine
erfolgreiche LocalAuthentication-Prüfung wird vor dem Lesen und Verifizieren des
Gerätegeheimnisses verlangt. Weil dasselbe Credential den ausdrücklich
gewählten passwortlosen Normalstart ermöglichen muss, ist der Keychain-Datensatz
nicht mit einer biometrischen Access-Control-Flag versehen. Die Grenze ist damit
eine echte OS-Authentifizierungsprüfung plus anschließende
Credential-Verifikation, aber keine behauptete Secure-Enclave- oder
biometryCurrentSet-Bindung des Geheimnisses.

Der Adapter verwendet bewusst den klassischen macOS-Schlüsselbund mit
anwendungsspezifischer ACL statt des Data-Protection-Keychains: Letzterer ist
ohne passende Keychain-Access-Group-Entitlements im weiterhin erlaubten
ad-hoc-signierten Pilotbuild nicht zuverlässig nutzbar. Der Datensatz setzt
keine Synchronisierung, wird nicht exportiert und kann wegen der getrennten
Store-/Epoch-Prüfung auch nach einem nicht löschbaren Restwert keine Sitzung
freigeben.

Registrierung ist kompensierbar: Zuerst wird ein nicht authentifizierender
`pending`-Datensatz angelegt, danach das Geheimnis und zuletzt der Datensatz
transaktional aktiviert; jeder Fehler widerruft `pending`, entfernt das
Geheimnis best effort und lässt keinen authentifizierenden Zwischenzustand zurück.
Deaktivierung und globale Widerrufe machen zuerst den Storezustand unwirksam und
löschen danach den Schlüsselbundeintrag best effort. Passwortänderung, Recovery,
Support-Reset und Neueinrichtung invalidieren über die monotone Security-Epoch
alle älteren Credentials, auch wenn ein Schlüsselbundeintrag nicht löschbar ist.

Security Store v3 ist eine additive, transaktionale Migration von v2. Fachliches
Restore und `.jkmbackup` enthalten oder verändern weder Credential-Metadaten
noch Geheimnisse. Es wird keine Datenbank-, Dokument- oder
Backupverschlüsselung eingeführt. Die physische 0.2B.4-Pilot-Mac-Abnahme samt
echtem Sleep/Wake bleibt offen.

## ADR-067 - Erste Schritte als lokale Orientierung, nicht als Fachassistent

**Status:** Fuer Sprint 0.2C.1 freigegeben und umgesetzt.

`Erste Schritte` ist eine Shell-interne Orientierung nach erfolgreicher
Authentifizierung und nach Aufbau der fachlichen Shell. Sie startet nicht vor
Login, nicht in `password_reset_pending`, nicht bei fail-closed
Security-Zustaenden, nicht im Restore-Worker und nicht automatisch im
isolierten Packaged-Smoke.

Der Flow besitzt hoechstens fuenf kurze Schritte und navigiert ausschliesslich
ueber vorhandene Shell-/Settings-Routen zu bestehenden Seiten. Es gibt keine
neue Hauptnavigation, keine Popup-Tour, keine Overlays ueber Schuelerdaten und
keine neue fachliche Bearbeitungsfunktion. Statushinweise duerfen nur
aggregierte technische Zustaende lesen und zeigen keine Schuelernamen,
Leistungswertung oder Prozentbewertung.

Der Fortschritt wird ausschliesslich in
`<runtime-root>/app-preferences.json` gespeichert:
`onboarding_status`, `onboarding_current_step` und
`onboarding_format_version`. Der Store bleibt ausserhalb von Security Store,
fachlicher SQLite, Support-Reset-Anfragen und `.jkmbackup`. Fachliches Restore,
Passwortwechsel, Recovery und Support-Reset veraendern den Onboarding-Status
nicht.

Bestehende Installationen ohne lokalen Onboarding-Status duerfen beim ersten
Start dieser neuen Produktversion einmal automatisch eingefuehrt werden.
`completed` und `dismissed` unterdruecken die automatische Anzeige. Manuelles
erneutes Oeffnen in den Einstellungen setzt den Status erst bei bewusster
Fortsetzung wieder auf `in_progress`.

Nicht eingefuehrt werden Import, Demo-/Pilotdatenerzeugung, automatische
Backups, fachliche Datenanlage, Support-Reset-UI, Keychain, Touch ID, Windows
Hello, persistente Anmeldung oder Verschluesselung.

## ADR-066 - Auth-Gate vor jeder fachlichen Initialisierung und fluechtige Sitzung

**Status:** Fuer Sprint 0.2B.4 freigegeben und umgesetzt.

Der produktive Start wird in eine technische Vor-Auth-Phase und die bestehende
fachliche Nach-Auth-Phase geteilt. Restore-Worker, Runtime-Pfade, Instanz-Lock
und Restore-Recovery bleiben zuerst. Danach duerfen nur Runtime-Root,
Security-Verzeichnis, Store und Marker
angelegt beziehungsweise validiert werden. Erst ein eindeutig authentifizierter
Security-Zustand gibt Pilotdaten, Produktverzeichnisse, Logging, fachliche
SQLite-Verbindung, Adapter, `AppShell`, `refresh_all()` und Hauptfenster frei.

Allgemeine lokale App-Voreinstellungen liegen in genau einem atomaren
`<runtime-root>/app-preferences.json` ausserhalb des Security-Verzeichnisses.
Der optionale `display_name` ist kein Kontoattribut und besitzt keine Bindung an
`user_id`, Passwort, Recovery, Support-Reset oder Rollen. Er wird erst nach
bestaetigter Kontoaufnahme gespeichert, als Klartext projiziert und bleibt wie
alle allgemeinen App-Voreinstellungen ausserhalb des fachlichen Backups.

Neuinstallation und vorhandene ungeschuetzte Installation unterscheiden sich
nur durch eine read-only Existenzpruefung technischer fachlicher Artefakte; die
fachliche Datenbank wird dafuer nicht geoeffnet. Die Kontoaufnahme verwendet
vorhandene Security-v2-Zustaende zweiphasig: Passwort und Recovery-Satz bleiben
bis zur Sicherungsbestaetigung `password_reset_pending`. Marker-/Store-
Asymmetrie, Korruption, unbekannte Version oder technischer Sicherheitsfehler
sind fail-closed ohne Reparatur oder erneute Kontoaufnahme.

Eine Sitzung enthaelt nur `user_id`, `installation_id` und `security_epoch` im
Arbeitsspeicher. Sie wird nicht gespeichert. Ein zentraler, Qt-freier
Session-Controller bewertet echte Eingaben, Inaktivitaet und Wake; ein Qt-
Adapter sammelt Events und Plattformzeit. Sperren versteckt alle fachlichen
Top-Level-Fenster opak, erhaelt deren In-Memory-State und zeigt nur eine
neutrale Loginflaeche. Passwortwechsel, Recovery und Support-Reset invalidieren
aeltere Epochen.

Laufende Backups duerfen unter Sperre enden; UI-Fortschritt bleibt verdeckt.
Unbestaetigte Restore-Vorschauen werden verworfen, bestaetigte Worker-Handoffs
nicht abgebrochen. Nach jedem Neustart und Restore ist eine neue
Authentifizierung erforderlich. Der Packaged-Smoke darf den interaktiven
Dialog nur nach doppelter Isolation durch Marker und nachweislich temporaere
Datenwurzel ersetzen; normale Paketdaten koennen diesen Pfad nicht nutzen.

Nicht eingefuehrt werden Keychain, Touch ID, Windows Hello, persistente
Geraete-/Sitzungstokens, `angemeldet bleiben`, Support-Reset-UI oder
Verschluesselung.

## ADR-065 - Offline signierter Support-Reset mit Ed25519

**Status:** Fuer den Qt-freien Core in Sprint 0.2B.3 freigegeben; UI,
Startintegration und Sitzung bleiben offen.

Ein Support-Reset verwendet keinen Masterzugang. Eine lokal erzeugte technische
Reset-Anfrage wird ausserhalb der App mit Ed25519 signiert. Private Schluessel
liegen ausschliesslich in getrennten Support-Werkzeugen und werden nur als
passphrasengeschuetztes PKCS#8 gespeichert; Repository, Build und App-Bundle
enthalten weder private noch produktive Testschluessel. Die App besitzt nur eine
versionierte Offline-Registry oeffentlicher Schluessel. Rotation und Widerruf
der Zustaende `active`, `retiring` und `revoked` erfolgen ausschliesslich durch
ein App-Update, nicht ueber Netzwerk oder Cloud.

Das Format `JKM-SR1.<payload>.<signature>` bindet kanonisch und signiert
Formatversion, Algorithmus, `key_id`, Installation, Nutzer, Reset-Anfrage,
Aktion, Erzeugungs- und Ablaufzeit sowie eine zufaellige Nonce. Anfragen gelten
hoechstens 24 Stunden; Tokens standardmaessig 30 Minuten und technisch
hoechstens zwei Stunden. Zwei Minuten Uhrtoleranz begrenzen unvermeidbare
Offline-Uhrabweichungen, koennen aber eine grob falsche lokale Uhr nicht sicher
erkennen. Token und Anfrage sind einmalig. Unbekannte Versionen, Algorithmen,
Aktionen, Schluessel und nicht kanonische Darstellungen werden ohne Fallback
abgelehnt.

Vor jeder Security-Aenderung muss der vorhandene Backup-Service ein fachliches
`.jkmbackup` erfolgreich erzeugen und vollstaendig verifizieren. Der Security
Store bleibt aus diesem Backup ausgeschlossen. Erst danach darf eine einzelne
Security-Transaktion Anfrage und Token-Digest verbrauchen, den alten
Passworthash unbrauchbar machen, das Konto auf `password_reset_pending` setzen,
alle aktiven und vorbereiteten Recovery-Saetze widerrufen, Drosselungszustaende
neutralisieren und die monotone Security-Epoch erhoehen. Fachliche Datenbank,
Dokumente, Backups, IDs und Restore-Vertraege bleiben unveraendert.

Die Security-Epoch bildet spaeter den Widerrufsanker fuer gespeicherte
Anmeldungen, Geraete- oder Sitzungstokens. `Auf diesem Geraet angemeldet
bleiben`, Keychain und optionales Touch ID werden in diesem Sprint nicht
eingefuehrt; die Inaktivitaetssperre bleibt spaeter aktiv und das Passwort
bleibt bei Touch ID der Fallback. Ein Support-Reset muss solche spaeteren
Anmeldungen durch Epoch-Wechsel widerrufen.

Sprint 0.2B.3 fuehrt keine UI, Startblockade, Sitzung, App-Beendigung, neues
Passwort oder neue Recovery-Codes ein.

## ADR-064 - Separate lokale Anwendungssperre als Security Core

**Status:** Freigegeben und in Sprint 0.2B.2 umgesetzt; produktive
Startintegration und UI bleiben offen.

Version 0.2 fuehrt eine Anwendungssperre, keine Dateiverschluesselung ein. Die
verbindliche Benutzerinformation lautet: „Die App-Sperre ist keine
Verschlüsselung der Datenbank, Dokumente oder Backups.“ Direkter Dateizugriff
bleibt moeglich; FileVault, geschuetztes OS-Konto und Geraeteverwaltung bleiben
notwendig.

Der Security Core ist eine eigenstaendige Domain-/Application-/Infrastructure-
Grenze mit separatem versioniertem SQLite Store unter
`<runtime-root>/security/security.sqlite` und nicht geheimem versioniertem
Enrollment-Marker. Er ist weder fachliche Datenquelle noch Bestandteil von
Backup, Restore, Export oder Diagnose. Fachliche Restore-Abläufe und
`DATABASE_COMPATIBILITY_VERSION = 1` bleiben unveraendert.

Version 0.2 erzwingt im Application Service genau ein aktives lokales Konto je
Installation. Installations- und Nutzer-ID sind unabhaengige zufaellige UUIDv4.
Passwoerter werden ausschliesslich mit Argon2id und explizitem PHC-/Formatvertrag
gespeichert; es gibt keinen Pepper, Fallback, Masterzugang oder Cloud-Reset.
Recovery verwendet zehn einmalige lokal gehashte Codes je Satz und eine
zweiphasige, crash-sichere Regeneration.

Die lokale Kalibrierung fuer Sprint 0.2B.2 verwendet 65536 KiB Memory,
Time Cost 6, Parallelism 1, 16-Byte-Salt und 32-Byte-Hash. Nach je einem
Aufwaermlauf lagen die Mittelwerte fuer Time Cost 4, 5 und 6 bei 147,17 ms,
182,80 ms und 219,78 ms. Time Cost 6 ist die kleinste gemessene ganzzahlige
Erhoehung im Zielkorridor von ungefaehr 200 bis 350 ms. Bestehende
Time-Cost-3-PHC-Hashes bleiben kompatibel und werden erst nach erfolgreicher
Verifikation aktualisiert; Schema- und Hashformatversion bleiben `1`.

Store-/Marker-Widersprueche, Korruption und unbekannte neuere Versionen sind
fail-closed. Die spaetere Startintegration muss die ungeschuetzte
Bestandsinstallation bewusst behandeln und wird in diesem Sprint nicht
vorweggenommen. Gezielt gemeinsames Loeschen von Store und Marker, Offline-
Hashangriffe und lokaler Zugriff auf unverschluesselte Fachdaten bleiben
dokumentierte Restrisiken.

## ADR-063 - Einstellungen als Übersicht mit einzelnem lokalem Arbeitsbereich

Status: Fuer Sprint 0.2A.4 freigegeben

`Einstellungen` bleibt ein bestehendes Hauptnavigationsziel, ist aber ausschliesslich eine Orientierung mit genau drei tastaturbedienbaren Karten: `Stundenplan`, `Fächer für die Dokumentation` und `Datensicherung`. Bearbeitung findet immer nur in einer lokalen Unterseite statt; Zurueck fuehrt sichtbar zur Übersicht, und ein erneutes Öffnen des Hauptziels beginnt wieder dort. Die Stundenplan- und Fachauswahlpfade behalten ihre vorhandenen Adapter, Commands und fachlichen Regeln.

Die Datensicherungsseite ist eine allgemeine Betriebsfunktion. `SettingsScreen` zeigt nur ViewModels, UI-Zustaende und Signale. `BackupRestoreDesktopAdapter` kapselt vorhandene Services, Runtime-Pfade, Prepared-Pruefung, Handoff und Worker-Start. Restore braucht Auswahl, Verifikation, Vorschau, ausdrueckliche Bestaetigung, Prepared-Pruefung und einmaligen Workerstart; der Worker erzeugt das verpflichtende Sicherheitsbackup vor jedem produktiven Austausch. Es gibt keine automatische Sicherung oder Aufbewahrung.

Sprint 0.2A.4a ergaenzt fuer potenziell lange technische Aufrufe einen shell-eigenen `BackupRestoreOperationsController`. Genau ein unveraenderlicher Auftrag laeuft ueber `QThread` und einen widgetfreien `QObject`-Worker in vorhandene Application-Services. Ergebnis- und Fehlerprojektion bleiben im Hauptthread. Der Controller kennt nur `idle`, `running` und `finishing`, haelt Thread und Worker bis zum echten Thread-Ende und verwendet ausschliesslich `quit()`/`deleteLater()`, niemals `terminate()` oder einen fachlich nicht abgesicherten Cancel. Dateiauswahl, Restore-Vorschau, Bestaetigung, Handoff, Prozessstart und kontrolliertes App-Schliessen bleiben im Hauptthread.

## ADR-062 - Journalgestuetzter Worker-Restore mit Rollback-Prioritaet

Status: Fuer Sprint 0.2A.3c freigegeben

Der produktive Restore laeuft ausserhalb der normalen PySide-Laufzeit in einem Qt-freien Worker. App und Worker verwenden denselben an der kanonischen Runtime-Wurzel gebundenen exklusiven Instanz-Lock; die App beendet vor der Worker-Uebergabe alle Datenbankzugriffe. Eine einmalige Handoff-Datei bindet Restore-ID, kryptografische Nonce, kanonische Runtime-Wurzel, Archivgroesse und -hash, Staging-State-Hash sowie Groesse und Hash der vorbereiteten V1-Datenbank. Der Worker leitet Live-, Staging-, Rollback-, Fehler- und Journalpfade ausschliesslich selbst ab und akzeptiert keine frei waehlbaren Zielpfade.

Der paketierte Start verwendet das eigene Bundle-Executable mit argv-Liste,
niemals einen Entwicklerpfad oder Shellstring. Ein erfolgreiches `Popen` und
`handoff_created` beweisen noch keine Uebernahme. Der Worker muss den
geerbten Lock-Descriptor vom Dateianfang validieren, den Handoff einmalig
authentisieren, `worker_started` journalen und dies ueber einen privaten
Ready-Kanal bestaetigen. Danach wartet er blockierend auf das EOF eines nur
von der Haupt-App gehaltenen Lebensdauerkanals. Erst das vollstaendige
Prozessende der Haupt-App erlaubt Preflight oder Datenmutation. Fehlende
Bestaetigung beendet und erntet den Worker, markiert den unmutierten Vorgang
als `aborted_before_replacement` und laesst die App geoeffnet.

Vor dem ersten produktiven Rename muessen Prepared-Staging, V1-Kompatibilitaet, Managed-File-Inventar, Pfad-Disjunktheit, Speicher, Schreibrechte, Live-SQLite-Integritaet, kontrollierter WAL-Checkpoint und ein vollstaendig verifiziertes Sicherheitsbackup bewiesen sein. Bis dahin bleiben die Live-Daten byteidentisch. Der Gesamtaustausch ist nicht physisch atomar; er besteht aus atomaren Einzel-Renames auf demselben Dateisystem und wird deshalb durch einen atomar ersetzten aktuellen Zustand sowie ein append-only JSONL-Ereignisjournal abgesichert. Vor jedem kritischen Rename werden Intent und Dateisystemzustand gefsynct, danach Rename und Completed-Zustand.

DB, `-wal`, `-shm` und `documents/` werden als getrennte technische Zustaende behandelt. Alte Daten werden nie geloescht, sondern in den Restore-gebundenen Rollbackbereich verschoben. Jeder Fehler vor einem erfolgreichen Startup-Handshake priorisiert den vollstaendigen Rollback. Kann der alte oder neue konsistente Zustand nicht anhand von Journal, Existenz, Groesse, Hash, SQLite-Pruefung und Dateiinventar bewiesen werden, lautet der Zustand `manual_recovery_required`; die normale App darf dann nicht starten und es findet keine automatische Bereinigung statt.

Start-Recovery laeuft vor Runtime-Vorbereitung, Logging, `QApplication`, Datenbankinitialisierung und Pilotdateninstallation. Ein installierter neuer Bestand wird erst nach einem einmaligen, kurzlebigen Resume-Token und erneuter read-only Pruefung von Datenbank und Dokumentinventar als `completed` markiert. Alte Pilot-V0-Daten werden weiterhin ausschliesslich im Staging migriert. Es werden keine fachlichen Daten transformiert, keine sichtbare UI und keine automatische Sicherung eingefuehrt.

## ADR-061 - Persistentes Restore-Staging vor jedem spaeteren Live-Austausch

Status: Fuer Sprint 0.2A.3b freigegeben

Restore-Staging veraendert niemals produktive Daten. Ein vollstaendig verifiziertes `.jkmbackup` wird in einen eindeutig per technischer Restore-ID gebundenen Bereich `restore-staging/<restore-id>/` innerhalb der aktuellen Runtime-Datenwurzel extrahiert. Dieser Bereich liegt ausserhalb der produktiven SQLite-Datei und ausserhalb von `documents/`; vorhandene Restore-Verzeichnisse werden nie ueberschrieben. Das technische `staging-state.json` enthaelt nur Restore-ID, Archivhash und -groesse, Format- und Kompatibilitaetswerte, Quell- und Ziel-`user_version`, Phase, aggregierte technische Counts und Zeitpunkte.

Unterstuetzt werden ausschliesslich exaktes V1 sowie der registrierte unversionierte `c029aff`-Vorgaenger. Exaktes V1 wird kontrolliert nach `prepared/` kopiert. Beim bekannten V0-Vorgaenger wird ausschliesslich die Staging-Datenbank in einer expliziten SQLite-Transaktion auf V1 migriert; der vollstaendige V0-Fingerprint wird vorher read-only bestaetigt und `PRAGMA user_version = 1` ist der letzte Migrationsschritt. Unbekannte, widerspruechliche oder neuere Schemata werden abgelehnt. Fachliche Werte, IDs, Counts, Bericht-/LEG-Snapshots und Snapshot-Hashes bleiben unveraendert.

Managed Files werden ausschliesslich ueber die verifizierten technischen Manifest-IDs materialisiert. Originalpfade werden nie als Ziel verwendet; Symlinks, Sonderdateien, Traversal und Hash- oder Groessenabweichungen werden abgelehnt. Finale Bericht- und LEG-PDFs behalten ihre vertraglichen runtime-relativen Artefaktpfade. Regulare Managed Documents erhalten einen sicheren technischen Zielpfad unter `prepared/documents/`; nur deren `documents.file_path` wird in einer eigenen Transaktion auf die spaetere aktuelle Runtime-Documents-Wurzel umgebogen. Externe Referenzen, PDF-Pfade, Snapshot-JSON und Snapshot-Hashes bleiben unveraendert.

Vor einem spaeteren Live-Austausch ist ein vollstaendig durch den vorhandenen `BackupService` erzeugtes und verifiziertes Sicherheitsbackup unter `backups/restore-safety/<restore-id>/` Pflicht. Sprint 0.2A.3b stellt diesen getrennten technischen Schritt bereit, verbindet ihn aber noch nicht mit einem Restore. Nicht freigegeben sind produktiver Austausch, Live-Renames, Restore-Journal, Worker, Instanz-Lock, Live-Rollback, Start-Recovery, App-Neustart oder sichtbare UI.

## ADR-060 - Datenbank-Kompatibilitaetsvertrag und isolierter Restore-Verifier

Status: Fuer Sprint 0.2A.3a freigegeben

Backupformat, Datenbank-Kompatibilitaet und App-Version sind unabhaengige Verträge. `BACKUP_FORMAT_VERSION = 1` beschreibt weiterhin ausschliesslich die unveraenderte `.jkmbackup`-Archivstruktur. `DATABASE_COMPATIBILITY_VERSION = 1` bezeichnet das registrierte produktive V1-Schema. `APP_VERSION` bleibt eine davon unabhaengige Produkt- und Paketversion.

`PRAGMA user_version` ist ab diesem Sprint die verbindliche Datenbankschemaversion. Eine neu erzeugte, zuvor schemafreie SQLite-Datenbank erhaelt `user_version = 1` innerhalb derselben Transaktion wie die V1-Schemaerzeugung. Eine bereits vorhandene Datenbank mit nicht-internen Schemaobjekten und `user_version = 0` bleibt historisch unversioniert und wird beim normalen Start weder adoptiert noch in-place migriert. Es gibt keine automatische Startmigration.

Die bekannte unversionierte Datenbankstruktur aus dem Stand `c029aff` ist ausschliesslich ueber ihren registrierten vollstaendigen Kompatibilitaetsfingerprint als V1-Vorgaengerkandidat anerkannt. Ein bekannter Vorgaenger liefert `MIGRATION_REQUIRED`, ist aber in diesem Sprint kein Migrationsauftrag. Unbekannte `user_version = 0`- oder `user_version = 1`-Schemata sowie Datenbanken mit einer Version groesser als `1` sind `INCOMPATIBLE`.

Der vollstaendige Restore-Fingerprint ist deterministisches kanonisches JSON mit SHA-256. Er umfasst alle nicht-internen Tabellen samt normalisiertem Tabellen-SQL, Spalten, Typen, `NOT NULL`, Defaults, Primaerschluesseln und Fremdschluesseln, ausserdem explizite Indizes samt Spalten und Partial-Praedikaten, Trigger und Views. Tabellen-SQL bindet insbesondere `CHECK`-Constraints. Ausgeschlossen bleiben Dateninhalte, SQLite-interne Tabellen und Indexnamen, Autoincrement-Zaehler sowie fluechtige SQLite-Werte. Der bestehende strukturelle Backup-Fingerprint aus Format v1 bleibt unveraendert.

Backup-Metadaten duerfen Kompatibilitaetsversion `1` nur aus einer read-only geprueften Snapshot-Datenbank ableiten. Exaktes V1 wird mit `sqlite_user_version = 1`, der registrierte unversionierte Vorgaenger mit `sqlite_user_version = 0` dokumentiert. Unbekannte oder neuere Datenbankstaende duerfen kein Backup mit einer falschen V1-Behauptung erzeugen. Bestehende gueltige Format-v1-Backups bleiben durch den bisherigen `BackupVerifier` verifizierbar.

Der neue `RestoreVerifier` ist ausschliesslich eine isolierte technische Verifikation und Vorschau. Er bindet Archivgroesse und SHA-256 an das bereits durch den `BackupVerifier` gepruefte Archiv, extrahiert sicher in ein kurzlebiges temporaeres Verzeichnis, oeffnet die Kandidatendatenbank nur read-only, vergleicht Manifest und tatsaechliche Datenbankversion, berechnet den vollstaendigen Fingerprint und prueft Integritaet, Fremdschluessel, Counts sowie Managed Files. Jede temporaere Datei wird bei Erfolg und Fehler entfernt. Die Vorschau enthaelt nur technische Versionen und aggregierte Counts, keine Namen, Texte, Dateinamen, IDs oder Pfade.

In ADR-060 selbst nicht freigegeben waren persistentes Restore-Staging, Migration, Pfad-Rebasing und Sicherheitsbackup; diese Grenze wird fuer die ausschliesslich technische Staging-Vorbereitung durch ADR-061 erweitert. Worker, Austausch der Live-Datenbank, Rollback, Journal, Start-Recovery, App-Neustart und sichtbare UI bleiben nicht freigegeben.

## ADR-059 - Verifiziertes ZIP-Backup als allgemeine Betriebsfunktion

Status: Fuer Sprint 0.2A.2 freigegeben

Das neue Anwendungsbackup ist eine allgemeine, ausdruecklich ausgeloeste Betriebsfunktion. Es liest die produktive SQLite-Datenbank und registrierte verwaltete Dateien, veraendert aber weder fachliche Daten noch Dokumente, Revisionen oder Artefakte. Die sichtbare PySide-Oberflaeche und das bestehende geschlossene Shell-Backup bleiben unveraendert.

Die Datenbank wird ausschliesslich mit `sqlite3.Connection.backup()` in einen temporaeren Snapshot geschrieben. Eine normale Kopie der laufenden Datenbank, manuelle WAL-/SHM-Kopien, ein externer `sqlite3`-Prozess oder plattformspezifische Shellwerkzeuge sind fuer diesen Service ausgeschlossen. Der Snapshot muss `PRAGMA integrity_check` und `PRAGMA foreign_key_check` bestehen; blockierte Schreibtransaktionen werden nur begrenzt abgewartet und fuehren danach zu einem typisierten Betriebsfehler.

Das Archiv ist ein normales ZIP mit der Endung `.jkmbackup`, `backup_format_version = 1` und den Pfaden `manifest.json`, `database/kompetenzmanager.sqlite` sowie `files/<technical-id>.<neutral-extension>`. Das kanonische Manifest enthaelt technische Build-, Datenbank-, Schema-, Mengen- und Dateiintegritaetsinformationen, aber keine Schuelernamen, Lehrkraftnamen, Notizen, Beobachtungs- oder Berichtstexte, Originaldateinamen oder absoluten beziehungsweise externen Pfade.

Gesichert werden registrierte aktive und soft-deaktivierte Dokumentdateien innerhalb von `RuntimePaths.documents` sowie registrierte finale Bericht- und LEG-PDF-Artefakte. Registrierte externe Dokumentreferenzen werden nicht kopiert und nur als Anzahl samt `missing_count` dokumentiert. Freie Exporte, Logs, vorhandene Backups, frei gewaehlte Entwurfs-PDFs und unregistrierte Dateien sind kein Backup-Inhalt; unregistrierte Nutzdateien unter `documents/` oder fehlende beziehungsweise veraenderte verwaltete Dateien blockieren die Erstellung.

`sqlite_user_version`, ein deterministischer struktureller Schema-Fingerprint und `compatibility_version` dokumentieren den gesicherten Datenbankstand. Fuer explizite Indizes gehoert die stabil normalisierte Definition aus `sqlite_master.sql` einschliesslich eines Partial-Index-`WHERE`-Praedikats zur Struktur. SQLite-interne Indizes und fluechtige Schemawerte bleiben ausgeschlossen. Die Kompatibilitaetsversion ist in diesem Sprint ausdruecklich kein Restore-Vertrag. Restore, Restore-Vorschau, Migration, automatische Sicherung, Aufbewahrung, Verschluesselung, Signierung, Passwortschutz, Nutzerkonto, Import, Onboarding und Cloud bleiben nicht implementiert.

## ADR-058 - Eigenständiges macOS-Pilotpaket und getrennte Benutzerdaten

Status: Fuer den lokalen Apple-Silicon-Piloten umgesetzt

Der Jenaplan-Kompetenzmanager wird fuer den macOS-Piloten mit PyInstaller als eigenstaendige `.app` inklusive Python-, PySide6-, Qt- und PDF-Laufzeit gebaut. Die technische Pilotversion stammt ausschliesslich aus `src/version.py`; die stabile Bundle-ID lautet `de.jenaplan.kompetenzmanager`. Der erste Pilotbuild ist `arm64` und setzt macOS 13 voraus.

Das App-Bundle ist unveraenderlicher Programm- und Ressourcenbereich. Produktive Daten liegen ausschliesslich unter `~/Library/Application Support/Jenaplan-Kompetenzmanager/`. Eine vorhandene Benutzerdatenbank wird beim Start niemals durch Paket-, Start- oder Demodaten ersetzt. Der Entwicklerstart behaelt den bisherigen relativen Pfad unter `data/`.

Die Standard-Paketvariante `empty` enthaelt keine SQLite-Datei und erzeugt beim ersten Start eine leere produktive Datenbank mit den bereits freigegebenen Schema-, Stammdaten- und Katalogdefaults. Die Variante `demo` darf nur ueber die explizite Buildoption entstehen und verwendet ausschliesslich die fiktiven Daten aus `scripts/seed_test_data.py`. Die gebaute Variante wird im Bundle dokumentiert. Die Entwicklerdatenbank aus `data/` wird nie paketiert.

App-Aktualisierungen erfolgen im Piloten durch Ersetzen der `.app`; Benutzerdaten bleiben davon getrennt. Es gibt keinen Auto-Updater, keine automatische Wiederherstellung und keine automatische Loeschung von Benutzerdaten. Das technische Backup verlangt eine geschlossene App und sichert Datenbank und verwaltete Dokumente in einen neuen Zeitstempelordner.

Developer-ID-Signierung und Notarisierung erfolgen nur, wenn lokal eine echte geeignete Identitaet und separat konfigurierte Apple-Zugangsdaten vorhanden sind. Ohne Identitaet wird der Pilotbuild hoechstens ad-hoc signiert und der Gatekeeper-Status sichtbar dokumentiert. Zertifikate oder Geheimnisse sind nie Repositoryinhalt.

## ADR-001

Excel-Dateien werden ausschließlich durch Python erzeugt.

Keine manuellen Änderungen.

## ADR-002

VBA ist ausschließlich für UI-Aufgaben freigegeben.

Keine fachliche Logik in VBA.

## ADR-003

Historische Entscheidung: Microsoft Excel für macOS war die verbindliche Zielplattform.

Fuer die Hauptanwendung wird diese Entscheidung durch ADR-045 abgeloest. Excel bleibt Export-, Berichts- oder Legacy-Projektion.

## ADR-004

Die Projektentwicklung erfolgt sprintbasiert.

## ADR-005

Das Bewertungssystem besteht aus:

- `++`
- `+`
- `-`
- `--`

Die Darstellung erfolgt später über Ampelfarben.

## ADR-006

Alle Beziehungen im Datenmodell erfolgen über eindeutige IDs.

## ADR-007

Produktentscheidung.

Die Excel-Arbeitsmappe stellt die Benutzeroberfläche dar.

Die interne Datenstruktur darf technisch aufgebaut sein.

Die sichtbaren Arbeitsblätter orientieren sich ausschließlich an den Arbeitsabläufen der Lehrkraft.

## ADR-008

Produktentscheidung.

Die Stammgruppenübersicht bildet zukünftig eine zentrale Einstiegsansicht.

Bewertungen werden möglichst nur einmal erfasst.

Weitere Ansichten werden automatisch daraus erzeugt.

## ADR-009

Produktentscheidung.

Kompetenzen werden hierarchisch gespeichert.

Beispiel:

- Fach
- Lernbereich
- Kompetenzgruppe
- Kompetenz

## ADR-010

Produktentscheidung.

Das Datenmodell soll eine Entwicklungsdokumentation ermöglichen.

Mehrere Beobachtungen einer Kompetenz über einen längeren Zeitraum müssen zukünftig möglich sein.

## ADR-011

Produktentscheidung.

Die Software soll pädagogische Prozesse unterstützen.

Neue Funktionen werden danach bewertet, ob sie den Arbeitsalltag einer Lehrkraft vereinfachen.

## ADR-012 - Single Purpose Views

### Kontext

Während der Discovery-Phase und des UX-Entwurfs wurde festgestellt, dass Lehrkräfte je nach Situation unterschiedliche Ziele verfolgen:

- Im Unterricht soll möglichst schnell eine Beobachtung dokumentiert werden.
- Nach dem Unterricht soll die Kompetenzentwicklung analysiert werden.
- In der Stammgruppenübersicht soll lediglich ein Schüler ausgewählt werden.

Frühere Entwürfe versuchten, mehrere Aufgaben gleichzeitig auf einer Ansicht abzubilden.

Dadurch entstand unnötige Komplexität.

### Entscheidung

Jede Ansicht des Kompetenzmanagers verfolgt genau einen primären Zweck.

Jede zusätzliche Information oder Funktion wird daran gemessen, ob sie diesen Zweck unmittelbar unterstützt.

Neue Funktionen dürfen die Hauptaufgabe einer Ansicht nicht verwässern.

### Konsequenzen

Stammgruppenübersicht

- Primärer Zweck: Schüler schnell finden und auswählen.
- Keine Kompetenzbewertungen oder Analysen.
- Fokus auf schnelle Navigation.

Schülerprofil

- Primärer Zweck: Beobachtungen erfassen und Kompetenzentwicklung eines einzelnen Kindes verstehen.
- Einstieg über "Neue Beobachtung".

Kompetenzansicht

- Primärer Zweck: Entwicklung einer einzelnen Kompetenz nachvollziehen.

Schülerverwaltung

- Primärer Zweck: Schüler verwalten.
- Schüler hinzufügen, bearbeiten und archivieren.

Berichte

- Primärer Zweck: Vorbereitung pädagogischer Gespräche und Dokumentationen.

Dashboard

- Primärer Zweck: Handlungsbedarf sichtbar machen.

### Begründung

Dieses Prinzip reduziert die kognitive Belastung der Lehrkraft und sorgt dafür, dass jede Ansicht klar verständlich bleibt.

Neue Funktionen dürfen einer Ansicht nur hinzugefügt werden, wenn sie den primären Zweck dieser Ansicht unterstützen.

## ADR-013

Produktentscheidung.

Beobachtungen sind die fachliche Source of Truth.

Alle weiteren Informationen werden daraus abgeleitet.

## ADR-014

Produktentscheidung.

Eine Beobachtung kann mehreren Kompetenzen zugeordnet werden.

Begründung:

Eine Präsentation, Gruppenarbeit oder Lernzielkontrolle zeigt häufig mehrere Kompetenzen gleichzeitig.

Das Datenmodell muss diese Beziehung unterstützen.

## ADR-015

Produktentscheidung.

Kompetenzstände werden historisiert.

Frühere Entwicklungsstände werden nicht überschrieben.

Lernentwicklung soll nachvollziehbar bleiben.

## ADR-016

Produktentscheidung.

Die Benutzeroberfläche orientiert sich an den Arbeitsabläufen einer Lehrkraft.

Nicht an der internen Datenstruktur.

## ADR-017

Produktentscheidung.

Die Bewertungslogik bleibt zunächst:

- `++`
- `+`
- `-`
- `--`

Sie unterstützt den Alltag der Lehrkräfte.

Die eigentliche Lernentwicklung ergibt sich jedoch aus mehreren Beobachtungen über einen längeren Zeitraum.

## ADR-018

Produktentscheidung.

Die Software schlägt Kompetenzstände vor.

Die endgültige Festlegung erfolgt durch die Lehrkraft.

## ADR-019

Produktentscheidung.

Das Schülerprofil bildet den primären Arbeitsplatz.

Nicht Dashboard oder Stammgruppenmatrix.

## ADR-020

Produktentscheidung.

Die Benutzeroberfläche unterscheidet zwischen

- geplanten Beobachtungen
- spontanen Beobachtungen

## ADR-021 - UI-Technologie für UX-Prototypen ab v0.2

### Kontext

Der erste UX-Prototyp hat gezeigt, dass rein hyperlinkbasierte Arbeitsmappen für die nächste UX-Generation nicht ausreichen.

Die zweite Generation des UX-Prototyps wird auf Microsoft Excel für macOS ausgerichtet.

### Entscheidung

Python bleibt verantwortlich für:

- Workbook-Erzeugung
- Datenstruktur
- Styles
- Generierung
- Build-Artefakte

VBA übernimmt zukünftig ausschließlich:

- Navigation
- Dialoge
- Benutzerinteraktion
- UserForms

Fachliche Logik verbleibt vollständig im Python- und Datenmodell.

### Konsequenzen

VBA-Code darf keine fachlichen Regeln, Berechnungen, Kompetenzlogik oder Datenmodellentscheidungen enthalten.

Die Trennung zwischen Python-Generator, fachlichem Kern, UI-Screens und späteren VBA-Bausteinen wird vorbereitet, aber in Sprint 3.0 noch nicht groß refaktoriert.

Der bestehende Prototyp v0.1 bleibt als Referenz erhalten. Neue Arbeiten erfolgen ab v0.2.

## ADR-022 - Stammgruppenübersicht als Einstieg

### Kontext

Sprint 3.1 und Sprint 3.1a haben die damalige Klassenübersicht als erste Ansicht der zweiten UX-Prototyp-Generation konkretisiert. Ab Sprint 3.4 lautet die fachliche Bezeichnung `Stammgruppenübersicht`.

Das Review mit Product Owner und Jenaplan-Lehrkraft hat bestätigt, dass die Stammgruppenübersicht im Unterricht nur dann hilfreich ist, wenn sie schnell erfassbar bleibt und nicht zur Analyse- oder Verwaltungsansicht wird.

### Entscheidung

Die Stammgruppenübersicht ist ausschließlich der Einstieg in den Arbeitsablauf.

Ihre Aufgabe besteht darin:

- Schüler schnell zu finden
- Schüler auszuwählen
- anschließend in das Schülerprofil zu wechseln

Die Stammgruppenübersicht ist ausdrücklich:

- kein Dashboard
- keine Verwaltungsansicht
- keine Analyseansicht
- keine Auswertungsseite

### Konsequenzen

Die Stammgruppenübersicht enthält keine Kompetenzstände, Bewertungen, Analysen, Berichte, Statistiken oder Verwaltungsfunktionen.

Die gesamte Schülerkarte ist die spätere Klickfläche für den Wechsel ins Schülerprofil.

Ein separater Button innerhalb der Karte wird nicht verwendet.

## ADR-023 - Sortierung und Datenquelle der Stammgruppenübersicht

### Kontext

Lehrkräfte suchen Kinder im Unterricht überwiegend über den Vornamen.

Die Stammgruppenübersicht soll aus vorhandenen Schülerdaten entstehen und nicht manuell gepflegt werden.

### Entscheidung

Die Standardreihenfolge der Schüler in der Stammgruppenübersicht erfolgt alphabetisch nach Vorname.

Die Stammgruppenübersicht wird vollständig aus den vorhandenen Schülerdaten generiert.

Die technische Identität eines Schülers ist immer `student_id`.

Namen dienen nur Anzeige und Suche.

### Konsequenzen

Schülerkarten werden nicht manuell gepflegt.

Wenn Schüler in der Schülerverwaltung hinzugefügt, bearbeitet oder archiviert werden, aktualisiert sich die Stammgruppenübersicht automatisch aus diesen Daten.

Die Stammgruppenübersicht besitzt keine eigene Geschäftslogik.

Die verborgene Datenquelle der Stammgruppenübersicht ist eine abgeleitete UI-Projektion und darf keine eigene Schülerdaten-Quelle werden.

Alle Änderungen an Schülerdaten erfolgen über die Schülerverwaltung. Eine physische Löschung ist nicht vorgesehen.

## ADR-024 - Schülerverwaltung als separater Bereich

### Kontext

Die Stammgruppenübersicht soll im Unterricht schnelles Finden und Auswählen ermöglichen.

Verwaltungsfunktionen würden diesen Zweck verwässern.

### Entscheidung

Die Verwaltung von Schülern erfolgt künftig in einem separaten Bereich `Schülerverwaltung`.

Dort können Lehrkräfte:

- Schüler anlegen
- Schüler bearbeiten
- Schüler archivieren

### Konsequenzen

Die Stammgruppenübersicht enthält bewusst keine Verwaltungslogik.

Ein freigegebener Navigationsabsprung zu einer separaten Schuelerverwaltungs- oder Dialogseite ist zulaessig, solange die Stammgruppenübersicht selbst keine Schuelerdaten bearbeitet, validiert oder speichert.

Die Schülerverwaltung ist der einzige UI-Ort für Änderungen an Schülerdaten. Schüler werden nicht physisch gelöscht, sondern archiviert.

## ADR-025 - Design Freeze Stammgruppenübersicht

### Kontext

Die Stammgruppenübersicht wurde unter der früheren Bezeichnung Klassenübersicht in Sprint 3.1 erstellt und in Sprint 3.1a auf Grundlage eines UX-Reviews für den Unterricht optimiert.

Laura hat das aktuelle Layout in Sprint 3.4 ausdrücklich freigegeben. Es gilt als Referenzdesign.

### Entscheidung

Die folgenden Eigenschaften der Stammgruppenübersicht dürfen in normalen Entwicklungssprints nicht verändert werden:

- Desktop-Anmutung
- Farbwelt
- Kartenlayout
- Kartenabstände
- Kartenhöhe
- Informationshierarchie
- Farbkonzept
- Typografie
- 4-spaltiges Raster
- Suchfeld
- Weißraum
- 140-%-Zoom der Stammgruppenübersicht
- kompakte Darstellung für Stammgruppen bis mindestens 28 Schüler

### Konsequenzen

Neue Ansichten orientieren sich am freigegebenen Referenzdesign.

Designänderungen erfolgen ausschließlich in einem eigenen UX-Sprint mit UX-Review und Product-Owner-Freigabe.

## ADR-026 - Schnellzugriff Neue Beobachtung

### Kontext

Im Unterricht soll eine Beobachtung schnell dokumentiert werden können.

Die Stammgruppenübersicht bleibt der Einstieg zum Finden und Auswählen eines Schülers.

Das Schülerprofil bleibt der vollständige Arbeitsbereich.

### Entscheidung

Eine Funktion besitzt genau eine Implementierung.

Eine Funktion darf jedoch mehrere Einstiegspunkte besitzen.

Die Funktion `Neue Beobachtung` kann künftig über die Stammgruppenübersicht und über das Schülerprofil gestartet werden.

Beide Einstiege öffnen denselben zentralen Beobachtungsdialog.

### Konsequenzen

Die Stammgruppenübersicht darf eine Kontextaktion `Neue Beobachtung` besitzen.

Diese Aktion arbeitet immer auf dem ausgewählten Schüler.

Die Stammgruppenübersicht startet keinen eigenen Beobachtungsprozess und enthält keine eigene Beobachtungslogik.

Sie übergibt ausschließlich `student_id` an den zentralen Beobachtungsdialog.

Der Beobachtungsdialog existiert projektweit nur einmal.

Das Datenmodell ändert sich dadurch nicht.

Alle Beobachtungen bleiben ausschließlich über `student_id` mit dem jeweiligen Schüler verknüpft.

## ADR-027 - Einführung von VBA als Interaktionsschicht

### Kontext

Die aktuelle UX-Prototyp-Generation wird als `.xlsx` durch Python erzeugt.

Diese Lösung funktioniert für statische Layouts, abgeleitete UI-Projektionen und einfache Formellogik.

Mit wachsender Interaktion entstehen jedoch technische Einschränkungen:

- Navigation ist an Zellpositionen gebunden.
- Hyperlinks können keine dynamische `student_id` übergeben.
- Dynamische Karten erschweren robuste Navigation.
- Der zentrale Dialog `Neue Beobachtung` ist ohne Interaktionsschicht nur mit Workarounds umsetzbar.
- Formeln und Hilfsspalten übernehmen zunehmend Aufgaben, die eigentlich UI-Interaktion sind.

### Variantenbewertung

#### Variante A: Python + `.xlsx` + Formeln

Stärken:

- Makrofrei.
- Einfach zu erzeugen.
- Geringere Sicherheitsbarrieren beim Öffnen.
- Gut geeignet für statische UI-Projektionen, Layouts und lesende Ansichten.

Schwächen:

- Navigation bleibt positionsgebunden.
- Keine robuste dynamische Übergabe von `student_id`.
- Dialoge und echte Benutzerinteraktion sind nur eingeschränkt möglich.
- Formeln werden schnell schwer wartbar.
- UX-Interaktion wandert in Hilfszellen und Schattentabellen.

#### Variante B: Python + `.xlsm` + VBA

Stärken:

- VBA kann `student_id` gezielt aus der UI-Projektion lesen und weitergeben.
- Navigation kann unabhängig von sichtbarer Kartenposition erfolgen.
- Ein zentraler Beobachtungsdialog kann projektweit einmal implementiert werden.
- UserForms und Ereignisse passen fachlich zur geplanten Excel/macOS-Desktop-Anwendung.
- Python kann weiterhin Workbook, Datenmodell, UI-Projektionen, Styles und Build-Artefakte erzeugen.

Schwächen und Risiken:

- `.xlsm` bringt Makro-Sicherheitsdialoge und organisatorische Freigaben mit sich.
- VBA-Entwicklung und Test auf macOS müssen explizit geprüft werden.
- Automatisches Erzeugen einer `.xlsm` mit VBA benötigt ein gültiges `vbaProject.bin` oder eine freigegebene Excel/VBA-Projekt-Injektion.
- Fachlogik darf nicht in VBA abwandern.

### Entscheidung

Für den Jenaplan-Kompetenzmanager wird VBA als Interaktionsschicht empfohlen.

Python bleibt verantwortlich für:

- Workbook-Erzeugung
- Datenmodell
- UI-Projektionen
- Styles
- Build-Artefakte

VBA übernimmt ausschließlich:

- Navigation
- Übergabe von `student_id`
- Dialogstart
- UserForms
- Benutzerinteraktion

Fachlogik, Datenmodellentscheidungen, Kompetenzlogik und Beobachtungsableitungen verbleiben vollständig im Python-/Datenmodell.

### Konsequenzen

Die Produktlinie sollte von `.xlsx` auf `.xlsm` erweitert werden, sobald der VBA-Spike technisch validiert ist.

Die bestehende `.xlsx`-Datei bleibt als Referenz- und Fallback-Artefakt erhalten.

Ein VBA-Proof-of-Concept muss vor einer breiten Umstellung zeigen:

- bestehendes Design bleibt unverändert,
- Zoom der Stammgruppenübersicht kann auf 140 % gesetzt werden,
- Klick auf eine sichtbare Schülerkarte funktioniert unabhängig von ihrer Position nach der Suche,
- `student_id` wird als einziger technischer Schlüssel übergeben,
- Schülerprofil öffnet sich,
- Zurück-Link funktioniert,
- keine Fachlogik entsteht in VBA.

### Spike-Ergebnis in dieser Umgebung

Microsoft Excel für macOS ist lokal installiert und per AppleScript erreichbar.

Ein vollständig automatisierter `.xlsm`-PoC konnte in dieser Umgebung noch nicht erzeugt werden, weil kein bestehendes `vbaProject.bin` vorhanden ist und die programmgesteuerte VBA-Projekt-Injektion nicht erfolgreich validiert werden konnte.

Der technische Packaging-Spike bestätigt die Hürde:

- Im Repository existiert aktuell kein `vbaProject.bin`, keine `.xlsm`-Vorlage und kein exportiertes VBA-Projekt.
- Die bestehende `Jenaplan_UX_Prototype_v0.2.xlsx` enthält kein `xl/vbaProject.bin`, keine VBA-Relationship und keinen macro-enabled Content-Type.
- `openpyxl` kann ein vorhandenes VBA-Projekt beim Laden mit `keep_vba=True` erhalten und beim Speichern wieder in eine `.xlsm` übernehmen.
- `openpyxl` kann kein neues VBA-Projekt erzeugen und keine `.bas`-, `.cls`- oder UserForm-Quellen zu einem gültigen `vbaProject.bin` kompilieren.
- Eine bloß umbenannte oder leere `.xlsm` ohne eingebettetes VBA-Projekt gilt nicht als valider PoC.

Für einen reproduzierbaren `.xlsm`-Build ist daher ein einmalig erzeugter und validierter VBA-Seed erforderlich.

Der bevorzugte Build-Prozess ist:

1. VBA-Quellen zusätzlich lesbar im Repository pflegen, zum Beispiel unter `vba/`.
2. Das VBA-Projekt einmalig in Microsoft Excel für macOS in einer Macro-enabled-Arbeitsmappe erstellen und testen.
3. Das daraus entstehende `vbaProject.bin` oder eine minimale `.xlsm`-Seed-Datei als Build-Artefakt versionieren.
4. Python erzeugt weiterhin Workbook, Datenmodell, UI-Projektionen und Styles.
5. Der Packaging-Schritt lädt den Seed mit `keep_vba=True` oder übernimmt das vorhandene `vbaProject.bin` in die generierte Arbeitsmappe.
6. Die erzeugte `.xlsm` wird technisch geprüft: `xl/vbaProject.bin`, macro-enabled Content-Type, VBA-Relationship und Smoke-Test in Excel für macOS.

Bis dieser Seed existiert, bleibt die `.xlsx`-Datei das verlässliche Build-Artefakt. Die `.xlsm`-Linie wird erst eingeführt, wenn der Packaging-Prozess mit echtem VBA-Projekt validiert ist.

## ADR-028 - Konsolidierte Zielarchitektur und Entwicklungsreihenfolge

### Kontext

Die UX-Prototyp-Generation ab v0.2 richtet sich vollständig auf Microsoft Excel für macOS aus.

Die Architekturarbeit zu VBA hat bestätigt, dass Interaktion, Dialoge und UserForms langfristig nicht sauber über reine `.xlsx`-Formeln abgebildet werden können.

Gleichzeitig bleibt das Datenmodell die fachliche Grundlage des Produkts.

### Entscheidung

Historische Entscheidung: Microsoft Excel für macOS war die verbindliche Zielplattform fuer die damalige UX-Prototyp-Generation.

Fuer die Hauptanwendung wird diese Entscheidung durch ADR-045 abgeloest.

Python bleibt verantwortlich für:

- Build-System
- Workbook-Erzeugung
- Datenmodell
- UI-Projektionen
- Styles
- Berichte
- Fachlogik

VBA übernimmt nach erfolgreichem Packaging ausschließlich:

- Navigation
- Buttons
- Dialoge
- UserForms
- Benutzerinteraktion

Keine Fachlogik wird in VBA implementiert.

Das Datenmodell bleibt vollständig unabhängig von VBA.

### Datenmodell-Prinzip

Das Datenmodell ist die fachliche Grundlage des Projekts.

Neue UI-Elemente, Formeln, Hilfstabellen, VBA-Routinen und Screens dürfen das Datenmodell niemals umgehen.

Alle Ansichten sind Projektionen des Datenmodells.

### Entwicklungsreihenfolge

Jede Implementierung folgt künftig dieser Reihenfolge:

1. Vision
2. Product Discovery
3. Produktentscheidung
4. Datenmodell-Review
5. Architektur-Review
6. UX-Review
7. Prompt-Review
8. Implementierung
9. Technical Review
10. Test
11. Commit

### Konsequenzen

Bis ein validierter VBA-Seed existiert, bleibt `.xlsx` das produktive Build-Artefakt.

Nach erfolgreichem Packaging kann die `.xlsm`-Linie als Interaktionsschicht eingeführt werden, ohne Python, Datenmodell oder Fachlogik zu ersetzen.

### Validierung

Sprint 3.3b hat praktisch bestätigt, dass Microsoft Excel für macOS, Python und VBA technisch zusammenarbeiten:

- Ein manuell in Excel erzeugter `.xlsm`-Seed wurde mit `openpyxl` und `keep_vba=True` geladen.
- Python konnte die Arbeitsmappe verändern und wieder als `.xlsm` speichern.
- Das eingebettete `xl/vbaProject.bin` blieb erhalten.
- Das Makro lief anschließend in Microsoft Excel für macOS.

Sprint 3.3c bereitet die `.xlsm`-Linie als Zielartefakt vor. `.xlsx` bleibt Fallback, bis das VBA-Framework stabil ist.

Die lesbaren VBA-Quellen liegen unter `vba/modules/`. Sie ersetzen nicht das binäre `vbaProject.bin`; für ausführbaren VBA-Code muss der Seed nach Import der Module in Excel aktualisiert werden.

Die Bereinigung von VBA-Projektobjekten wie Workbook- und Worksheet-CodeNames erfolgt im Zweifel manuell im VBA-Editor. Python darf das binäre `vbaProject.bin` erhalten und strukturell prüfen, aber nicht durch nicht validierte Binärmanipulationen verändern.

## ADR-029 - Design-System als Source of Truth

### Kontext

Laura hat den aktuellen UX-Prototypen begutachtet und das Design der Stammgruppenübersicht ausdrücklich freigegeben.

Das freigegebene Design soll künftig nicht in normalen Entwicklungssprints verändert werden.

### Entscheidung

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.

Das freigegebene Referenzdesign umfasst insbesondere:

- Farbwelt
- Typografie
- Kartenlayout
- Kartenabstände
- Desktop-App-Anmutung
- 140-%-Zoom der Stammgruppenübersicht
- Suchfeld
- Weißraum
- visuelle Hierarchie

Neue Ansichten müssen sich daran orientieren.

Designänderungen dürfen künftig ausschließlich über einen eigenen UX-Sprint erfolgen.

### Konsequenzen

Normale Entwicklungssprints verändern das Design nicht.

Die Dokumentation des Design-Systems liegt in `docs/DESIGN_SYSTEM.md`.

Python erzeugt weiterhin die Benutzeroberflächen aus dem freigegebenen Design-System.

## ADR-030 - Stammgruppe und Kurs als eigenständige Domänenentitäten

### Kontext

Laura hat das fachliche Modell präzisiert.

Die bisher verwendete Bezeichnung `Klasse` ist fachlich nicht genau genug.

### Entscheidung

Die Domänensprache ersetzt `Klasse` vollständig durch `Stammgruppe`.

Jeder Schüler gehört genau einer Stammgruppe an.

Jeder Schüler gehört zusätzlich genau einem Kurs an.

Der Kurs beschreibt den Jahrgang.

Die Stammgruppe beschreibt die organisatorische Zugehörigkeit.

Stammgruppe und Kurs sind eigenständige fachliche Entitäten.

### Datenmodell-Konsequenzen

Student enthält:

- `student_id`
- Vorname
- Nachname
- `stammgruppe_id`
- `kurs_id`

Stammgruppe enthält:

- `stammgruppe_id`
- Name

Kurs enthält:

- `kurs_id`
- Name
- optionale Farbe für spätere UI

Die `student_id` bleibt technische Identität.

Das Datenmodell bleibt Source of Truth.

### UI-Konsequenzen

Die bisherige Klassenübersicht heißt künftig `Stammgruppenübersicht`.

Die Stammgruppenübersicht zeigt Schüler einer Stammgruppe. Die Kartenfarbe orientiert sich künftig am Kurs. Die Suche bleibt unverändert.

Zusätzlich wird eine neue Hauptansicht `Kursübersicht` aufgenommen.

Die Kursübersicht zeigt alle Schüler eines Kurses unabhängig von der Stammgruppe. Auf jeder Schülerkarte wird die Stammgruppe angezeigt.

Beide Ansichten greifen auf dieselben Schülerdaten zu. Es existieren keine doppelten Daten.

Die Ansichten sind ausschließlich Projektionen des Datenmodells.

### Verwaltungsfunktionen

Die Schülerverwaltung umfasst:

- Schüler anlegen
- Schüler bearbeiten
- Schüler archivieren

Schüler werden nicht physisch gelöscht.

Die Stammgruppenverwaltung umfasst:

- Stammgruppe anlegen
- Stammgruppe bearbeiten
- Stammgruppe archivieren

Neue Stammgruppen werden über die Stammgruppenverwaltung angelegt, nicht automatisch beim Anlegen eines Schülers.

Die Kursverwaltung umfasst:

- Kurs anlegen
- Kurs bearbeiten
- Kurs archivieren

Spätere Erweiterungen wie Farben und Jahrgänge bleiben möglich.

## ADR-031 - Dokumentation geht Implementierung voraus

### Kontext

Sprint 4 legt die Core Data Architecture als verbindliche Grundlage fuer spaetere Produktfunktionen fest.

Ohne dokumentierte Datenquellen, technische Namen, View Ownership und Data Lifecycles wuerden spaetere Sprints erneut lokale technische Entscheidungen treffen.

### Entscheidung

Dokumentation geht Implementierung voraus.

Neue Funktionen werden kuenftig erst nach der Architekturpruefung und Registry-Erweiterung umgesetzt.

Die verbindliche Reihenfolge lautet:

1. `PROJECT_CONSTITUTION.md` pruefen
2. `TECHNICAL_NAMES.md` pruefen
3. `DATA_REGISTRY.md` erweitern
4. `DATA_LIFECYCLE.md` ergaenzen
5. `VIEW_DATA_OWNERSHIP.md` ergaenzen
6. `UI_DATA_MAPPING.md` ergaenzen
7. erst danach Implementierung

### Begruendung

Die Architektur soll zukuenftige Implementierungen vereinfachen und Inkonsistenzen verhindern.

Funktionen sollen datengetrieben entstehen und keine eigenen Schattenmodelle, lokalen Zwischendaten oder kreativen technischen Namen einfuehren.

### Konsequenzen

Keine neue Datenquelle ohne `DATA_REGISTRY.md`.

Keine neue technische Bezeichnung ohne `TECHNICAL_NAMES.md`.

Keine neue Ansicht ohne `VIEW_DATA_OWNERSHIP.md`.

Keine neue UI-Komponente ohne `UI_DATA_MAPPING.md`.

Kein Schreibprozess ohne `DATA_LIFECYCLE.md`.

Feature-Sprints duerfen bestehende Legacy-Namen nicht spontan umbenennen.

## ADR-032 - Entity-first-Architektur

### Kontext

Ab Sprint 4 soll die erste produktnahe Umsetzung auf einer stabilen Datenarchitektur aufsetzen.

Wenn neue Funktionen zuerst als Masken gedacht werden, entstehen leicht lokale Datenhaltung, Schattenlogik und technische Namen ausserhalb der Registry.

### Entscheidung

Funktionen werden von Entitaeten und Datenfluessen aus gedacht, nicht von Masken.

Die verbindliche Reihenfolge lautet:

```text
Entity
-> Storage
-> Builder
-> UI-Projektion
-> VBA-Navigation
```

### Konsequenzen

Neue Verwaltungsfunktionen beginnen mit der Frage, welche Entitaet entsteht oder erweitert wird.

UI wird erst nach Entity, Storage und Builder-Projektion entworfen.

## ADR-033 - Builder als eigene Architekturschicht

### Kontext

Python erzeugt Workbook, Datenquellen, Styles und UI-Projektionen.

Diese Verantwortung muss als eigene Schicht sichtbar bleiben, damit Datenmodell und Excel-UI nicht vermischt werden.

### Entscheidung

Der Builder ist die verbindliche Schicht zwischen Daten und Workbook/UI.

```text
Data
-> Builder
-> Workbook/UI
-> VBA-Interaktion
```

Der Builder erzeugt Hidden Data Sheets, Excel-Tabellen, Named Ranges, UI-Projektionen und vorbereitete Navigationspunkte.

### Konsequenzen

Der Builder enthaelt keine spontane Fachlogik ausserhalb der Data Registry.

VBA greift nicht direkt auf fachliche Tabellen zu.

UI-Projektionen werden aus registrierten Datenquellen erzeugt.

## ADR-034 - Historisierung von Bezeichnern bleibt offene Entscheidung

### Kontext

Kurse, Stammgruppen und Kompetenzen koennen spaeter umbenannt werden.

Beobachtungen und Berichte koennen historische Kontexte anzeigen.

### Entscheidung

Noch nicht final entschieden ist, ob historische Beobachtungen bei geaenderten Kompetenznamen, Kursnamen oder Stammgruppennamen den aktuellen Namen oder den damals gueltigen Namen anzeigen.

Diese Entscheidung muss vor produktiver Beobachtungserfassung getroffen werden.

### Offene Frage

Wenn Kompetenznamen, Kursnamen oder Stammgruppennamen spaeter geaendert werden, zeigen historische Beobachtungen dann den aktuellen Namen oder den damals gueltigen Namen?

### Konsequenzen

Sprint 4.1 darf keine produktive Beobachtungserfassung einfuehren, ohne diese Frage vorher zu klaeren.

Schueler-, Kurs- und Stammgruppenverwaltung muessen stabile IDs erhalten, unabhaengig von sichtbaren Namen.

## ADR-035 - Modale UserForms und studentenzentrierte Dokumentreferenzen

### Kontext

Sprint 5 bereitet die erste echte Eingabemaske des Kompetenzmanagers vor.

Der Kompetenzmanager soll als Anwendung verstanden werden.

Excel ist die Runtime, nicht der Ort fuer direkte fachliche Eingaben in Tabellen.

Gleichzeitig sollen Dokumente und Medien spaeter angebunden werden, ohne Excel-Dateien durch eingebettete Anlagen zu belasten.

### Entscheidung

Fachliche Eingaben erfolgen ueber modale VBA-UserForms.

UserForms sammeln Eingaben, fuehren nur einfache Oberflaechenvalidierung durch und rufen freigegebene Services auf.

UserForms enthalten keine Businesslogik und schreiben nicht direkt in fachliche Workbook-Tabellen.

Die erste Referenz-UserForm ist `frm_student_new` fuer den Zielzustand `Neuer Schueler`.

Dateien werden nicht in Excel eingebettet.

Dokumente und Medien werden studentenzentriert im Dateisystem abgelegt.

Excel speichert nur Referenzen und Metadaten in `data_media`.

Beobachtungsanhaenge liegen ebenfalls unter dem Schueler und tragen zusaetzlich den Bezug zur Beobachtung.

### Konsequenzen

`data_media` wird als bestehende Datenquelle fuer Dokument- und Medienreferenzen vorbereitet.

Der Schuelerbezug `student_id` wird fuer Dokumente und Medien verbindlich.

Ein Beobachtungsanhang besitzt zusaetzlich `observation_id`.

Der Beobachtungsdialog wird nur vorbereitet und nicht in Sprint 5 implementiert.

Kompetenzen muessen im Beobachtungsdialog zwingend mitgedacht werden.

Schnellbeobachtung und Gruppenbewertung bleiben Backlog-Themen.

## ADR-036 - Sprint 5.1b stoppt an fehlender VBA-zu-Python-Service-Bruecke

### Kontext

Sprint 5.1b sollte `frm_student_new` erstmals produktiv an die Schueleranlage anbinden.

Der vorgesehene Ablauf war:

```text
UserForm
-> StudentService.create_student()
-> StudentRepository
-> tbl_students
-> aktualisierte Stammgruppenuebersicht
```

Die UserForm darf dabei keine Businesslogik enthalten und niemals direkt in `tbl_students` schreiben.

### Befund

`StudentService` ist aktuell eine Python-Laufzeitkomponente.

Die produktive UserForm laeuft in Excel/VBA.

Im Projekt existiert noch kein freigegebener, validierter Mechanismus, mit dem VBA auf macOS den Python-`StudentService` direkt, reproduzierbar und releasefaehig aufrufen kann.

Eine direkte Tabellenlogik in VBA waere ein Architekturbruch, weil dadurch die freigegebene Service-/Repository-Schicht umgangen wuerde.

### Entscheidung

Sprint 5.1b wird an dieser Stelle technisch gestoppt.

Historischer Stand: `frm_student_new` wurde nicht produktiv angebunden, solange keine freigegebene Bruecke zwischen VBA-UserForm und fachlicher Python-Schicht entschieden war.

Dieser Stopp bezog sich auf die inzwischen verworfene primaere VBA-UserForm-Strategie. Fuer worksheet-basierte Dialogseiten definiert ADR-043 den Runtime Adapter und den Refresh Contract.

Es wird kein Workaround umgesetzt, der in VBA direkt in fachliche Tabellen schreibt.

### Technische Optionen

Python Build/Import Workflow:

- Eingaben werden nicht live aus VBA verarbeitet.
- Python bleibt alleiniger Schreiber der Workbook-Datenquellen.
- Vorteil: passt zur bestehenden Architektur.
- Nachteil: kein echter Live-Dialog in der geoeffneten Excel-Datei.

VBA Repository-Schicht:

- VBA erhaelt eine eigene, eng begrenzte Repository-Schicht fuer freigegebene Schreibprozesse.
- Vorteil: echter Live-Dialog in Excel moeglich.
- Nachteil: fachliche Regeln muessen streng aus VBA herausgehalten und gegen Python-Regeln abgesichert werden.

CSV/Hidden-Sheet Command Queue:

- VBA schreibt nur einen technischen Befehl in eine Queue; Python verarbeitet ihn spaeter ueber Services.
- Vorteil: UserForm bleibt duenn und Service-Logik bleibt in Python.
- Nachteil: benoetigt einen klaren Synchronisations- und Aktualisierungsprozess.

SQLite/API:

- Excel/VBA spricht mit einer externen Daten- oder Service-Schicht.
- Vorteil: sauberer Anwendungsschnitt.
- Nachteil: groesserer Technologiesprung und zusaetzlicher Betrieb.

### Empfehlung

Empfohlen wird als naechster Architekturspike die Command-Queue-Variante.

Sie haelt die UserForm duenn, vermeidet direkte VBA-Tabellenschreiblogik und laesst `StudentService` weiterhin die fachliche Schueleranlage koordinieren.

Vor produktiver Schueleranlage muss entschieden werden:

- wo die Command Queue liegt
- wann Python sie verarbeitet
- wie die Stammgruppenuebersicht danach aktualisiert wird
- wie Fehler aus `StudentValidator` wieder in den Dialog oder an die Nutzerin gemeldet werden

### Konsequenzen

Sprint 5.1b fuehrt keine produktive Schueleranlage ein.

`OpenNewStudentDialog()` und `frm_student_new` bleiben vorbereitet, aber ohne produktiven Schreibpfad.

Der naechste Schritt ist eine Architekturentscheidung zur Laufzeitbruecke zwischen Excel/VBA und Python-Service-Schicht.

## ADR-037 - SQLite als moegliche zentrale Datenbasis geprueft

### Kontext

Sprint 5.2a prueft SQLite als technische Grundlage fuer spaetere UserForm-Schreibprozesse.

Der Zielpfad lautet:

```text
VBA UserForm
-> Python Bridge / CLI
-> SQLite DB
-> Python Builder
-> Excel-Projektion
```

VBA darf dabei nicht direkt in SQLite schreiben.

Python bleibt die fachliche Schreibschicht.

### Entscheidung

SQLite wird als moegliche neue Source of Truth weiterverfolgt.

Der Spike erzeugt eine SQLite-Datenbank unter `data/kompetenzmanager.sqlite`.

Der urspruenglich vorgeschlagene Pfad `Daten/kompetenzmanager.sqlite` wird nicht eingefuehrt, weil das Projekt bereits die Konvention `data/` fuer Datenartefakte verwendet.

Im Spike werden nur die bestehenden Entitaeten Student, Group und Course abgebildet:

- `students`
- `groups`
- `courses`

Die bestehenden IDs bleiben unveraendert:

- `STU-000001` usw.
- `GRP-000001` usw.
- `CRS-000001` usw.

### Befund

Python kann die SQLite-Datenbank erzeugen.

Python kann Seed-Daten fuer Students, Groups und Courses in SQLite schreiben.

Python kann diese Daten ueber SQLite-Repositories lesen.

Der bestehende Builder kann aus den SQLite-gelesenen Daten die bisherige Excel-Projektion erzeugen.

Die Excel-Projektion bleibt dabei weiterhin eine Projektion und wird nicht zur fachlichen Source of Truth.

### Konsequenzen

SQLite ist noch nicht produktive Source of Truth.

Die Workbook-Tabellen `tbl_students`, `tbl_groups` und `tbl_courses` bleiben im Spike Projektions- und Kompatibilitaetsschicht fuer Excel.

Wenn SQLite produktiv eingefuehrt wird, muss es genau eine fachliche Source of Truth geben:

- entweder SQLite als Storage und Excel als Projektion
- oder der aktuelle Workbook-Storage

Ein paralleler Schreibbetrieb in SQLite und Workbook-Tabellen ist nicht erlaubt.

### Risiken

- Historischer Stand: Python Bridge / CLI fuer UserForms war zu diesem Zeitpunkt noch nicht entschieden. Fuer worksheet-basierte Dialogseiten definiert ADR-043 den Runtime Adapter und den Refresh Contract.
- Fehler aus Python-Validierung muessen spaeter kontrolliert an Excel/VBA zurueckgemeldet werden.
- Dateiablage, Backup, Sperren und Mehrfachzugriff der SQLite-Datei sind noch nicht geklaert.
- Vollstaendige Migration weiterer Entitaeten, insbesondere Beobachtungen, Kompetenzen und Dokumentreferenzen, ist nicht Teil dieses Spikes.
- Der produktive Buildpfad darf erst umgestellt werden, wenn SQLite als Source of Truth final freigegeben ist.

### Empfehlung

SQLite soll als Zielarchitektur fuer die fachliche Datenhaltung weiter geprueft werden.

Der naechste sinnvolle Sprint ist ein Python-Bridge-/CLI-Spike:

- UserForm erzeugt keinen direkten Datenbankzugriff.
- VBA startet oder uebergibt spaeter nur einen technischen Auftrag.
- Python verarbeitet den Auftrag, nutzt Services und Repositories und aktualisiert SQLite.
- Der Builder erzeugt danach die Excel-Projektion aus SQLite.

## ADR-038 - Application Command Layer zwischen Adaptern und Domain Services

### Kontext

Nach dem SQLite-Spike braucht der Kompetenzmanager eine technische Bruecke zwischen Excel/VBA und der Python-Domaene.

Eine CLI ist dafuer nur ein moeglicher Adapter.

Die fachliche Steuerung darf nicht in CLI, VBA oder Excel-Logik wandern.

### Entscheidung

Zwischen Command-Adaptern und Domain Services wird ein Application Command Layer eingefuehrt.

Zielarchitektur:

```text
VBA
-> Command Adapter
-> Application Command Dispatcher
-> Domain Services
-> Repositories
-> SQLite
-> Builder
-> Excel-Projektion
```

Python bleibt die einzige fachliche Schreibschicht.

VBA enthaelt keine Businesslogik.

SQLite bleibt Zielarchitektur fuer fachliche Datenhaltung.

Excel bleibt Projektions- und UI-Schicht.

### Struktur

Empfohlene Struktur:

```text
src/application/
|-- dispatcher.py
`-- commands/
    |-- student.py
    |-- observation.py
    `-- report.py
```

`dispatcher.py` enthaelt den Application Command Dispatcher.

`commands/` enthaelt reine Command-DTOs, zum Beispiel `CreateStudentCommand` fuer `student.create`.

### Dispatcher-Design

Der Dispatcher nimmt ein Command mit `command_name` entgegen.

Er kennt keine Fachlogik.

Er leitet das Command an einen registrierten Handler weiter.

Der Handler ist die Verbindung zum passenden Domain Service, zum Beispiel:

```text
student.create
-> StudentService.create_student()
```

Der Dispatcher erzeugt keine IDs selbst, validiert keine Fachregeln und schreibt nicht in SQLite.

### CLI-Design

Eine spaetere CLI, zum Beispiel `python3 km.py student create`, ist nur ein Adapter.

Die CLI darf:

- Argumente entgegennehmen
- daraus ein Command-DTO bauen
- das Command an den Dispatcher uebergeben
- technische Fehlercodes und Meldungen zurueckgeben

Die CLI darf nicht:

- fachliche Regeln enthalten
- direkt Repositories aufrufen
- direkt in SQLite schreiben
- Excel-Projektionen selbst veraendern

### VBA-Anbindung

VBA ruft spaeter keinen Domain Service direkt auf.

VBA sammelt UI-Eingaben und uebergibt sie an einen Command Adapter.

Der Adapter uebergibt ein Command an den Dispatcher.

VBA bleibt Interaktionsschicht und enthaelt keine Businesslogik.

### Konsequenzen

Sprint 5.3 fuehrt keine produktive CLI und keine UserForm-Anbindung ein.

Der Application Layer ist ein Architektur-Skelett und noch keine vollstaendige Command-Menge.

Der naechste sinnvolle Sprint prueft einen konkreten Adapter fuer `student.create`, bevorzugt als CLI-/Python-Bridge-Spike.

## ADR-039 - student.create durchlaeuft den Python-Application-Stack

### Kontext

Sprint 5.4 prueft `student.create` ohne CLI, ohne VBA und ohne Excel.

Nachgewiesen werden soll nur der Python-Stack:

```text
ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService.create_student()
-> SQLiteStudentRepository
-> SQLite
```

### Entscheidung

`student.create` wird als erster End-to-End-Command im Python-Stack akzeptiert.

Der Dispatcher enthaelt keine Fachlogik und kein SQL.

Der Dispatcher liefert ein `SuccessResult`, wenn der Handler erfolgreich durchlaeuft.

Der Dispatcher liefert ein `ErrorResult`, wenn Domain- oder Repository-Fehler entstehen.

`StudentService` bleibt fuer fachliche Validierung, ID-Erzeugung und Prozesskoordination verantwortlich.

`SQLiteStudentRepository` ist fuer den Schreibzugriff auf SQLite verantwortlich.

### Konsequenzen

SQLite kann im Python-Stack als Source of Truth fuer `student.create` verwendet werden.

Adapter fehlen weiterhin:

- keine CLI
- keine VBA-Anbindung
- kein Prozessstart aus Excel
- keine Rueckmeldung an eine UserForm

Der naechste Sprint kann den ersten Adapter fuer `student.create` pruefen, ohne die fachliche Logik aus dem Python-Stack herauszuziehen.

Offen bleiben:

- Prozessstart aus Excel/VBA auf macOS
- Fehler-Rueckmeldung vom Python-Prozess an VBA
- Transaktionsgrenzen bei SQLite-Schreibprozessen
- anschliessender Rebuild oder Refresh der Excel-Projektion

## ADR-040 - Architecture Baseline v2.0

Status: Accepted

### Motivation

Die urspruengliche Excel-zentrierte Loesung war als schneller UX- und Workbook-Prototyp richtig.

Mit wachsendem Funktionsumfang reicht eine reine Workbook-Architektur aber nicht mehr aus:

- fachliche Schreibprozesse wie Schueleranlage, Beobachtungserfassung und Dokumentreferenzen brauchen stabile Transaktionen
- VBA darf keine Businesslogik enthalten
- Excel darf keine fachlichen Datenentscheidungen treffen
- fachliche Daten duerfen nicht gleichzeitig in UI-Projektionen und Tabellenlogik entstehen
- spaetere UserForms brauchen einen sauberen Weg in die Python-Domaene

Die Architektur wurde deshalb kontrolliert erweitert, ohne die bisherigen Erkenntnisse zu verlieren: Excel bleibt Zieloberflaeche und Projektion, Python bleibt fachliche Schicht, SQLite wird als zentrale Datenbasis vorbereitet.

### Architecture v1

Die erste tragfaehige Architektur war:

```text
Python
-> Workbook Builder
-> Excel
```

Python erzeugte Workbook-Struktur, Datenblaetter, UI-Projektionen und Styles.

Excel war Zielartefakt und sichtbare Arbeitsoberflaeche.

Diese Architektur bleibt historisch wichtig, weil sie die datengetriebene Projektion, strukturierte Tabellen, stabile IDs und reproduzierbare Builds eingefuehrt hat.

### Architecture Baseline v2.0

Die aktuell validierte Baseline lautet:

```text
                    Adapter Layer
           (VBA / CLI / zukuenftige Adapter)

                         |

               Application Layer
              (Dispatcher / Commands)

                         |

                  Domain Layer
             (Services / Validatoren)

                         |

              Infrastructure Layer
              (SQLite / Repository)

                         |

               Projection Layer
               (Workbook Builder)

                         |

                    Excel UI
```

### Verantwortlichkeiten

Adapter Layer:

- nimmt Benutzerinteraktionen oder technische Aufrufe entgegen
- baut Commands fuer die Application-Schicht
- enthaelt keine Fachlogik
- schreibt nicht direkt in SQLite

Application Layer:

- definiert Commands
- routet Commands ueber den Dispatcher
- erzeugt `SuccessResult` oder `ErrorResult`
- enthaelt keine Businesslogik, kein SQL und keine Excel-Logik

Domain Layer:

- enthaelt die fachliche Logik
- validiert Eingaben ueber Validatoren
- koordiniert fachliche Prozesse ueber Services
- erzeugt fachliche IDs nach freigegebener Strategie

Infrastructure Layer:

- kapselt Persistenz
- enthaelt Repositories
- liest und schreibt SQLite
- ist die einzige Schicht mit direktem Datenbankzugriff

Projection Layer:

- erzeugt Workbook-Datenblaetter, strukturierte Tabellen, Named Ranges und UI-Projektionen
- liest aus registrierten Datenquellen
- enthaelt keine Fachlogik

Excel UI:

- zeigt Projektionen
- ermoeglicht Navigation und Interaktion
- trifft keine fachlichen Datenentscheidungen
- ist nicht Source of Truth

### Architekturprinzipien

- SQLite ist die vorbereitete Source of Truth fuer fachliche Daten.
- Python ist die einzige fachliche Schreibschicht.
- Excel enthaelt keine fachlichen Datenentscheidungen.
- VBA enthaelt keine Businesslogik.
- Repositories kapseln Persistenz.
- Builder erzeugen ausschliesslich Projektionen.
- Commands bilden den Einstiegspunkt fachlicher Ablaeufe.
- Adapter sind austauschbar und duerfen keine Fachlogik enthalten.
- Es gibt keine parallele fachliche Schreibquelle neben SQLite.

### Standard-Datenfluss

Der Standardablauf fuer zukuenftige Schreibprozesse ist:

```text
User
-> worksheet-basierte Dialogseite oder freigegebener Adapter
-> Adapter
-> Dispatcher
-> Command
-> Service
-> Repository
-> SQLite
-> Builder
-> Excel-Projektion
```

### Auswirkungen

Alle zukuenftigen Module folgen dieser Baseline.

Das gilt insbesondere fuer:

- Schueler
- Beobachtungen
- Kompetenzen
- Dokumente
- Berichte

Sonderarchitekturen sind nicht zulaessig.

Neue Module muessen entweder in diese Schichten eingeordnet werden oder vorab eine explizite Architekturentscheidung erhalten.

### Abgrenzung

Diese Baseline fuehrt keine neue Implementierung ein.

Sie dokumentiert den bereits validierten Stand aus:

- SQLite Architecture Spike
- Application Command Layer
- `student.create` End-to-End durch den Python-Stack

Historischer Stand bei Annahme der Baseline: Offen blieben Adapter, produktive CLI, VBA-Prozessstart, UserForm-Anbindung und automatischer Refresh der Excel-Projektion. ADR-043 klaert Runtime Adapter und Refresh Contract fuer `student.create`; die konkrete Implementierung bleibt offen.

## ADR-041 - UX-Prototyp als verbindlicher Schritt vor UserForm-Umsetzung

Status: Superseded by ADR-042

### Kontext

Feature 1 `Neuer Schueler` soll als erste produktive UserForm des Kompetenzmanagers entstehen.

Die UserForm ist Teil des Adapter Layers und darf keine Fachlogik, keine direkte Tabellenlogik und keine SQLite-Kommunikation enthalten.

Gleichzeitig muss das visuelle Verhalten vor der technischen Umsetzung mit Laura bzw. dem Product Owner abgestimmt werden.

### Entscheidung

Fuer neue UserForms wird ein UX-Prototyp als verbindlicher Zwischenschritt eingefuehrt.

Der Ablauf lautet:

1. UX-Prototyp erstellen
2. UX-Review mit Laura bzw. Product Owner durchfuehren
3. UX-Freigabe dokumentieren
4. VBA-UserForm moeglichst 1:1 nach dem freigegebenen UX-Prototyp umsetzen
5. Validierung, Adapter-Anbindung und fachliche Logik erst danach ergaenzen

Der UX-Prototyp ist keine technische Implementierung.

Er ist die visuelle Referenz fuer die spaetere UserForm.

Designentscheidungen fuer UserForms werden im UX-Prototyp getroffen, nicht frei im VBA-Designer.

### Feature-1-Stand

Die Datei `output/Jenaplan_UX_Prototype_v0.1.xlsx` enthaelt das Blatt `Feature 1 – Neuer Schüler`.

Dieses Blatt dient als visuelle Vorlage fuer die spaetere UserForm `frm_student_new`.

Enthalten sind:

- Fenstertitel
- Pflichtfelder Vorname, Nachname, Stammgruppe und Kurs
- Notizbereich
- Dokumentbereich mit Empty State
- Button `+ Dokument hinzufügen`
- Buttons Abbrechen und Speichern

### Auswirkungen

Zukuenftige UserForms duerfen nicht mehr frei gestaltet werden.

Die technische VBA-Umsetzung muss sich an der freigegebenen UX-Prototyp-Seite orientieren.

Validierung, Adapter-Anbindung und fachliche Schreibprozesse werden erst nach der UX-Freigabe umgesetzt.

### Abgrenzung

Diese Entscheidung fuehrt keine Implementierung ein.

Es wurden keine Python-Quellen, keine VBA-Quellen, keine UserForms, kein Build und kein Seed geaendert.

## ADR-042 - Worksheet-basierte Dialogseiten als primaeres Eingabe-Pattern

Status: Accepted

### Kontext

Feature 1 `Neuer Schueler` sollte urspruenglich als VBA-UserForm `frm_student_new` umgesetzt werden.

Die praktische Pruefung auf Microsoft Excel fuer macOS hat gezeigt:

- der lokale VBA-Editor bietet den UserForm-Designer nicht verlaesslich an
- automatisch erzeugte MSForms-Controls werden in der Zielumgebung nicht belastbar als sichtbare Dialogoberflaeche gerendert
- der UserForm-Testoeffner konnte zwar zuletzt starten, die angezeigte Maske blieb aber leer
- AppleScript-Tests mit `do Visual Basic` sind in diesem Projekt fuer diesen Pfad nicht belastbar

Der UserForm-Ansatz wird deshalb fuer Feature 1 nicht weiter als primaerer Eingabedialog verfolgt.

### Entscheidung

Primaeres Eingabe-Pattern fuer Excel auf macOS sind ab Feature 1 worksheet-basierte Dialogseiten.

Beispiel:

```text
dlg_neuer_schueler
```

Diese Dialogseiten:

- sehen wie modale Dialoge aus
- liegen als eigene geschuetzte Arbeitsblaetter in der Excel-Datei
- sammeln Eingaben
- enthalten keine Businesslogik
- schreiben nicht direkt in fachliche Tabellen
- rufen spaeter ueber VBA bzw. einen freigegebenen Adapter den Python Command Layer auf
- werden nach Speichern oder Abbrechen wieder verlassen

### Architecture Baseline v2.0

Die Baseline bleibt bestehen.

Der Adapter Layer kann in Excel ueber VBA-Navigation, worksheet-basierte Dialogseiten oder zukuenftige Adapter umgesetzt werden.

VBA enthaelt weiterhin keine Businesslogik.

Excel bleibt UI und Projektion, nicht fachliche Source of Truth.

### Status von `frm_student_new`

`frm_student_new.frm` bleibt vorerst als experimenteller Artefaktstand erhalten.

Die UserForm ist deprecated und nicht produktiv freigegeben.

Sie wird nicht geloescht, bis ein eigener Bereinigungs- oder Migrationsschritt freigegeben ist.

### Konsequenzen

Feature 1 verwendet `dlg_neuer_schueler` als neue technische Zieloberflaeche.

Der UX-Prototyp `output/Jenaplan_UX_Prototype_v0.1.xlsx`, Blatt `Feature 1 – Neuer Schüler`, bleibt die visuelle Referenz.

Validierung, Speichern, Python Command, SQLite-Schreibzugriff, Dokument-Upload und Refresh bleiben separate spaetere Features.

## ADR-043 - Runtime Adapter und Refresh Contract fuer `student.create`

Status: Accepted

### Kontext

Feature 1.4 `Schueler speichern` wurde gestoppt, weil zwar der Python-Stack fuer `student.create` bis SQLite validiert ist, aber der produktive Runtime-Pfad aus Excel und der Refresh der geoeffneten Arbeitsmappe noch nicht freigegeben waren.

Offene Fragen waren:

- Wie ruft Excel/VBA den Python Command Layer auf?
- Wie wird die geoeffnete Excel-Projektion nach erfolgreichem Speichern aktualisiert?
- Wie bleibt der Projection Builder alleiniger Eigentuemer der Projektion?
- Wie wird direkte Tabellen-Schreiblogik in VBA verhindert?

### Entscheidung: Runtime Adapter

Der produktive Runtime-Pfad fuer Feature 1 lautet:

```text
Worksheet-Dialogseite
-> VBA Adapter
-> Python CLI/Bridge
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Regeln:

- VBA liest Dialogwerte ausschliesslich ueber registrierte Named Ranges.
- VBA verwendet keine festen Zelladressen.
- VBA baut keine fachlichen IDs selbst.
- VBA validiert keine Fachregeln.
- VBA schreibt nicht direkt in SQLite.
- VBA schreibt nicht direkt in fachliche Workbook-Tabellen.
- Die Python CLI/Bridge ist Adapter zur Application-Schicht und enthaelt keine Fachlogik.
- Der Dispatcher ruft den registrierten `student.create`-Handler auf.
- `StudentService` bleibt Ort der fachlichen Regeln.
- `SQLiteStudentRepository` bleibt Ort des Schreibzugriffs auf SQLite.

### Entscheidung: Refresh Contract

Der primaere Refresh-Vertrag ist Option C:

```text
Python Command erfolgreich
-> SQLite aktualisiert
-> Python Projection Builder erzeugt Projection-Refresh-Paket
-> VBA importiert ausschliesslich Projection Output in die geoeffnete Arbeitsmappe
-> Excel zeigt aktualisierte Projektion
```

Das Projection-Refresh-Paket ist ein von Python erzeugtes technisches Artefakt.

Es enthaelt ausschliesslich Builder-Output fuer registrierte Projektionsziele.

VBA darf daraus nur kopieren:

- registrierte `data_*`-/`tbl_*`-Projektionskopien, soweit sie aus SQLite erzeugt wurden
- registrierte UI-Projektionsbereiche und Named Ranges
- temporaeren UI-State wie Suchfeld und Dialogeingaben zuruecksetzen

VBA darf dabei nicht:

- Projektionen selbst sortieren, filtern oder berechnen
- fachliche IDs erzeugen
- fachliche Daten pruefen
- direkt SQLite lesen oder schreiben
- `tbl_students` als fachliche Source of Truth behandeln

SQLite ist fuer diesen Schreibprozess die fachliche Source of Truth.

Die Excel-Arbeitsmappe enthaelt nach dem Refresh nur eine Projektion aus SQLite.

Der Projection Builder bleibt Eigentuemer der Projektion.

### Bewertete Alternativen

Option A: Python erzeugt eine neue `output/latest.xlsm`, Benutzer oeffnet neu.

- Zulaessig als Fallback.
- Nicht primaer, weil der geoeffnete Workflow unterbrochen wird und Feature 1.4 nach erfolgreichem Speichern zur Stammgruppenuebersicht zurueckkehren soll.

Option B: VBA liest aktualisierte Daten direkt aus SQLite und baut die Ansicht.

- Abgelehnt.
- Das wuerde SQLite-Zugriff und Projektionslogik nach VBA verschieben.

Option C: Python erzeugt strukturierte Projektion, VBA aktualisiert nur Projektionsbereiche.

- Akzeptiert.
- Erhaelt Python als fachliche Schreib- und Projection-Builder-Schicht.
- Erlaubt Aktualisierung der geoeffneten Arbeitsmappe ohne direkte fachliche Tabellenlogik in VBA.

### Fehlerfall

Wenn der Python Command fehlschlaegt:

- SQLite bleibt konsistent.
- Es wird kein Projection-Refresh-Paket importiert.
- Der Dialog bleibt geoeffnet.
- VBA zeigt nur die Fehlermeldung aus dem Adapter-Ergebnis an.
- Dialogwerte bleiben erhalten.

Wenn der Command erfolgreich ist, aber der Projection Refresh fehlschlaegt:

- SQLite bleibt erfolgreich aktualisiert.
- VBA darf keine eigene Projektion erzeugen.
- VBA zeigt eine technische Refresh-Fehlermeldung.
- Option A darf als Fallback angeboten werden: neu erzeugte Arbeitsmappe oeffnen.

### Konsequenzen fuer Feature 1.4

Feature 1.4 darf produktiv implementiert werden, wenn es diesen Vertrag einhaelt:

- Dialogwerte nur ueber Named Ranges
- VBA Adapter ohne Fachlogik
- Python CLI/Bridge als Adapter zum Dispatcher
- `student.create` ueber bestehenden Application-/Domain-/Repository-Stack
- SQLite als Source of Truth
- Refresh nur ueber Python-generierten Projection Output
- keine direkte fachliche Tabellenbearbeitung durch VBA

## ADR-044 - PySide6 Desktop-App-Spike als alternativer UI-Adapter validiert

Status: Validated Spike

### Kontext

Der Excel/VBA-Runtime-Adapter fuer `student.create` wurde bis SQLite umgesetzt, zeigte aber auf macOS eine hohe technische Reibung beim Prozessstart und bei stabilen Dialogoberflaechen.

Vor einer weiteren Vertiefung des Excel/VBA-Runtime-Pfads wurde auf Branch `spike/python-gui` ein alternativer Desktop-Adapter geprueft.

Ruecksprungpunkt fuer den Excel-/xlwings-Pfad:

- `checkpoint-excel-adapter-before-python-gui`

### Validierter Pfad

Der PySide6-Spike wurde manuell validiert.

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Nachgewiesener Stand:

- App startet.
- Maske `Neuer Schüler` funktioniert.
- Ein Schuelerdatensatz wurde in SQLite geschrieben.
- Speichern nutzt den bestehenden Application-/Service-/Repository-Stack.
- Tests sind gruen: `python3 -m pytest` mit 26 bestandenen Tests.
- Build ist gruen.
- Commit `5363e18` und Tag `spike-pyside6-student-create` sichern den Spike-Stand.

### Regeln

PySide6 ist ein validierter alternativer UI-Adapter.

Die GUI darf:

- Daten anzeigen
- Eingaben sammeln
- Commands erzeugen
- den `ApplicationCommandDispatcher` aufrufen
- Fehler sichtbar anzeigen

Die GUI darf nicht:

- Businesslogik enthalten
- fachliche IDs erzeugen
- direkt aus Widgets in SQLite schreiben
- Services, Validatoren oder Repositories umgehen
- Excel/VBA/Builder/Seed-Dateien loeschen oder ersetzen

### Auswirkungen

Excel/VBA bleibt im Repository erhalten.

Excel bleibt bestehende Projektion und moeglicher Export-/Berichtspfad.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut.

Die Architecture Baseline v2.0 bleibt gueltig: Adapter sind austauschbar, Python bleibt fachliche Schreibschicht, SQLite bleibt Source of Truth, der Projection Builder bleibt Eigentuemer der Excel-Projektion.

### Offen

Historischer Stand: Diese offenen Punkte wurden durch ADR-046 fuer die Hauptanwendung entschieden.

Weiterhin offen bleiben produktiver Nutzer-Datenbankpfad, Backup/Restore, Packaging als macOS-App, Updates, Migrationen und der genaue Umfang kuenftiger Excel-Exporte.

Naechste Pruefpunkte:

- UX Hauptfenster
- Schuelerprofil
- Beobachtungsmaske
- Packaging als macOS-App
- Datenbankpfad produktiv
- Backup/Restore
- Excel-Export/Berichte

## ADR-045 - PySide6 als Hauptanwendung und Icon-basierte visuelle Leitlinie

Status: Accepted

### Kontext

Der PySide6-Spike wurde ueber mehrere Sprints zu einer nutzbaren Desktop-App-Linie erweitert.

Das freigegebene App-Icon gibt eine klare visuelle Richtung vor: Wachstum, Schuelerbezug, Kompetenzentwicklung und Auswertung in einer ruhigen, hochwertigen Desktop-App.

Die Excel-/VBA-Linie bleibt technisch wertvoll, erzeugt aber nicht die gewuenschte moderne Hauptanmutung fuer die Anwendung.

### Entscheidung

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Neue UI-Entwicklung konzentriert sich auf die PySide-App.

Excel/VBA ist nicht mehr die Zielrichtung fuer die Haupt-App. Excel kann weiterhin als Export-, Berichts- oder Legacy-Projektion bestehen.

Das freigegebene App-Icon ist die zentrale gestalterische Referenz fuer die Anwendung.

Leitregel:

> Der Jenaplan Kompetenzmanager wirkt wie eine moderne paedagogische Entwicklungs-App: ruhig, klar, wachstumsorientiert, datenbewusst und freundlich.

### Konsequenzen

- Neue Screens orientieren sich visuell an der Icon-Farbwelt und Symbolik.
- Die PySide-App soll nicht wie klassische Verwaltungssoftware oder Excel wirken.
- Dunkelblau, Blau, Tuerkis, Gruen, Orange und helle neutrale Hintergruende bilden die kuenftige Designrichtung.
- Karten, Panels, Dialoge, Profile, Beobachtungen und Auswertungen duerfen eine leichte moderne Glasoptik nutzen, solange Lesbarkeit und Kontrast gewahrt bleiben.
- Fachlogik bleibt ausserhalb der GUI in Application, Domain und Infrastructure Layer.
- Excel/VBA wird nicht geloescht, aber als Haupt-App-Pfad nicht weiter priorisiert.

## ADR-046 - PySide wird Hauptanwendung; Excel/VBA wird Legacy/Export

Status: Accepted

### Kontext

Das Projekt startete mit Excel, openpyxl und spaeter einem validierten VBA-Seed als schneller Prototyp- und Projektionspfad.

Der PySide-Prototyp hat sich ueber mehrere Sprints als deutlich geeigneter fuer eine ruhige, hochwertige und moderne paedagogische Desktop-App erwiesen.

Excel/VBA verursacht auf macOS relevante Plattform-, Automatisierungs- und Stabilitaetsrisiken, insbesondere bei UserForms, VBA-Automation und Smoke-Test-Pfaden.

Der Product Owner hat entschieden, dass PySide die Hauptanwendung des Jenaplan-Kompetenzmanagers wird.

### Entscheidung

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Excel ist nicht mehr Hauptanwendung.

Excel bleibt nur:

- Legacy-Artefakt
- Referenz aus der fruehen Projektphase
- Exportformat
- spaetere Berichtsausgabe, falls fachlich sinnvoll

Excel ist nicht mehr:

- primaere UI
- produktive Datenquelle
- Entwicklungsziel fuer neue Features
- Testziel fuer UI-Funktionalitaet

VBA wird nicht weiterverfolgt.

VBA wird nicht mehr verwendet fuer:

- neue Features
- UI
- Smoke-Tests
- Automatisierung
- produktive Workflows

### Konsequenzen

- Neue Features werden in PySide umgesetzt.
- Neue fachliche Daten laufen ueber Application, Domain, Repository und SQLite.
- Keine neuen VBA-/Excel-UI-Features.
- Keine VBA-Smoke-Tests als Zielpfad.
- Roadmap und Dokumentation werden auf PySide ausgerichtet.
- Excel-Generatoren, Workbook-Code, Seeds und VBA-Quellen werden nicht sofort geloescht, aber als Legacy-/Export-Pfad behandelt.
- `openpyxl` bleibt erlaubt, wenn ausdruecklich Export, Bericht oder Legacy-Altstand betroffen ist.
- Spaeter kann eine gezielte Bereinigung, Archivierung oder Entfernung alter Excel-/VBA-Pfade erfolgen.
- Packaging, Installer, Backup/Restore, Datenbankpfad und SQLite-Migrationen bleiben eigene spaetere Entscheidungen.

## ADR-047 - Excel/VBA wird aus dem aktiven Projektpfad archiviert

Status: Accepted

### Kontext

Nach der PySide-/SQLite-Entscheidung liegen aktive Produktentwicklung, Persistenz, Fachlogik, UI, Berichte und Tests in der PySide-Hauptanwendung.

Die frueheren Excel-/openpyxl-/VBA-Dateien wurden im aktiven Root nicht mehr fuer neue Features benoetigt und erschwerten die Projektstruktur sowie die Standardchecks.

### Entscheidung

Reine Excel-/VBA-Legacy-Dateien werden unter `legacy/excel/` archiviert.

Der alte Workbook-Build `build.py`, openpyxl-Projektionen, VBA-Quellen, Seed-Arbeitsmappen und zugehoerige Hilfsskripte gehoeren nicht mehr zum aktiven App-Pfad.

`python3 build.py` ist kein Pflichtcheck mehr.

Der aktive Standardcheck ist:

```text
git diff --check
python3 -m pytest
QT_QPA_PLATFORM=offscreen python3 -c 'from src.desktop_app.main import main; print("import ok")'
```

### Konsequenzen

- PySide/SQLite bleibt die Hauptanwendung und Source of Truth.
- `openpyxl` wird aus den aktiven Runtime-Abhaengigkeiten entfernt, solange kein aktiver Exportpfad es nutzt.
- Runtime- und Output-Dateien bleiben unversioniert.
- Excel-/VBA-Artefakte bleiben historisch nachvollziehbar, werden aber nicht fuer neue Features, UI, Smoke-Tests oder Standardbuilds verwendet.
- Ein spaeterer Exportauftrag muss neu fachlich und technisch freigegeben werden.

## ADR-048 - Fachliche Stufenzuordnung fuer Lehrplan-Kompetenzen

Status: Accepted

### Kontext

Sprint 4 bildet die Grundschul-Lehrplaene fachweise in beobachtbare Kompetenzen ab.

Die Lehrplaene unterscheiden haeufig Schuleingangsphase, Klassenstufe 4 oder fachliche Progressionen, die nicht in jedem Fach sauber trennbar sind.

Der Kompetenzkatalog muss diese Progression spaeter abbilden, ohne jahrgangsgemischte Gruppen oder individuelle Lernwege einzuschraenken.

### Entscheidung

Kompetenzen werden fachlich einer Lernstufe zugeordnet:

- `Klassenstufe 1-3`
- `Klassenstufe 4`
- `stufenuebergreifend`

`stufenuebergreifend` wird verwendet, wenn eine eindeutige Trennung fachlich nicht moeglich oder nicht sinnvoll ist.

Die spaetere UI filtert Kompetenzen, sperrt sie aber nie.

Die Standardansicht zeigt passende Kompetenzen. Klassenstufe 1-3 und Klassenstufe 4 werden unterscheidbar filterbar. Zusaetzlich gibt es `Alle Kompetenzen anzeigen`.

Klasse-4-Kompetenzen bleiben auch fuer juengere Kinder auswaehlbar.

### Konsequenzen

- Die Stufe ist eine fachliche Katalogeigenschaft.
- Die technische Speicherung wird spaeter entschieden.
- Jetzt entstehen keine CSV-Aenderung, keine SQLite- oder Schemaaenderung und keine UI-Umsetzung.
- Bestehende Kompetenz-IDs bleiben unveraendert.
- Bestehende Beobachtungen werden nicht migriert.
- Die Logik unterstuetzt jahrgangsgemischte Gruppen und individuelle Lernwege.

## ADR-049 - Produktbezogene Katalogstufe getrennt von Quellen-Geltungsbereich

Status: Accepted

### Kontext

Der aktuelle CSV-Katalog fuehrt `grade_band` als quellenbezogenen Geltungsbereich. Im bestehenden Katalog steht dort durchgaengig `1-4`.

Die Product-Owner-Entscheidung zur Stufenlogik verlangt dagegen eine spaetere Produktfilterung nach `Klassenstufe 1-3`, `Klassenstufe 4` und `stufenuebergreifend`.

Diese Filterlogik ist nicht identisch mit dem Quellenfeld `grade_band`.

### Entscheidung

`grade_band` bleibt Quellen- und Lehrplankontext.

Fuer die produktbezogene Filterlogik wird das technische Feld `learning_stage` empfohlen.

Empfohlener Wertebereich:

- `stage_1_3`
- `stage_4`
- `cross_stage`

Die sichtbaren UI-Texte werden daraus abgeleitet und bleiben deutsch.

### Konsequenzen

- Sprint 4A ergaenzt den CSV-Katalog um `learning_stage`.
- Sprint 4A migriert SQLite `competencies` um `learning_stage` und die Katalogmetadaten `catalog_status`, `catalog_default_active` und `activation_group_key`.
- `active` bleibt lokale Aktivitaet.
- `catalog_default_active` speichert den Standardwert aus dem Katalog.
- `activation_group_key` dient optional aktivierbaren Bereichen.
- `catalog_status` sieht zunaechst ausschliesslich `current` und `legacy` vor.
- UI, Berichte, Schuelerprofil, Dashboard und Dokumentationsstand koennen nach fachlicher Passung filtern, ohne Kompetenzen zu sperren.
- Bestehende Beobachtungen, bestaetigte Kompetenzstaende und Kompetenz-IDs werden nicht migriert.
- `grade_band` darf nicht fuer die App-Filterlogik ueberladen werden.
- Der idempotente Katalog-Upsert muss lokale Aktivierungsentscheidungen weiter schuetzen.

## ADR-050 - Bericht, Lernentwicklungsgespraech und PDF-Ausgabe

Status: Teilweise offen

Umgesetzt sind die Trennung von Live-Profil, Bericht, LEG und PDF-Renderer, persistente Bericht- und LEG-Drafts, getrennte unveraenderliche Bericht- und LEG-Revisionen sowie revisionsgebundene PDF-Artefakte. Offen bleiben die unten ausgewiesenen Produkt- und Betriebsentscheidungen; sie aendern den umgesetzten Kernvertrag nicht.

### Kontext

SQLite ist die produktive Source of Truth. Sprint 6 stellt eine kanonische Kompetenzstatus-Projektion bereit, die bestaetigte Kompetenzstaende, Beobachtungsvorschlaege und historische Kompetenzinformationen nachvollziehbar trennt. Das Schuelerprofil nutzt diese Daten bereits als Live-Arbeitsansicht; die bestehende Berichtsvorschau ist ebenfalls eine fluechtige Projektion.

Fuer offizielle Lernentwicklungsberichte reichen fluechtige Projektionen nicht aus. Ein freigegebener Bericht muss auch dann reproduzierbar und nachvollziehbar bleiben, wenn spaeter Beobachtungen ergaenzt, korrigiert oder deaktiviert, Kompetenzstaende neu bestaetigt oder Projektionsregeln weiterentwickelt werden.

Beobachtungen sind Evidenz, aber keine fertigen paedagogischen Aussagen. Automatische Vorschlaege duerfen weder finalen Berichtstext noch eine eigenstaendige Leistungsbewertung erzeugen. Bericht, LEG und Schuelerprofil duerfen keine voneinander abweichende Kompetenzlogik entwickeln.

### Architekturentscheidung

#### Schuelerprofil

Das Schuelerprofil bleibt eine Live-Arbeitsansicht. Es zeigt aktuelle Kompetenzstaende, Beobachtungen, Entwicklung, Dokumentationsabdeckung und Vorbereitungsmöglichkeiten. Es ist kein offizielles Dokument und kein reproduzierbarer Ausgabestand.

#### Bericht

Der Lernentwicklungsbericht wird langfristig eine eigene fachliche Entitaet. Diese Trennung ist erforderlich fuer:

- Reproduzierbarkeit eines freigegebenen Stands
- Versionierung und kontrollierte Korrekturen
- Nachvollziehbarkeit von Autorenschaft, Pruefung und Freigabe
- stabile PDF-Erzeugung
- Schutz vor nachtraeglichen Aenderungen an Beobachtungen, Kompetenzstaenden oder Projektionsregeln

Ein Bericht besitzt konzeptionell:

- Schuelerbezug
- Berichtszeitraum
- Autor
- Status `Entwurf`, `geprueft` oder `freigegeben`
- manuelle Texte
- bewusst ausgewaehlte Kompetenzinformationen
- bewusst ausgewaehlte Beobachtungsbelege
- Diagramme
- finale Ausgabeversion

Diese Begriffe sind in Sprint 7B fachliche Konzepte, keine freigegebenen SQLite-Felder oder neuen technischen Namen.

Die Live-Berichtsvorbereitung darf auf der kanonischen Kompetenzprojektion und einer zeitraumbezogenen Evidenzprojektion beruhen. Bestaetigte Kompetenzstaende bleiben von berechneten Beobachtungsvorschlaegen getrennt. Vorschlaege duerfen nur klar als Vorbereitung gekennzeichnet werden und werden nie automatisch zu finalem Berichtstext.

Spaetestens bei der Freigabe wird ein vollstaendiges Ausgabemodell eingefroren. Es enthaelt die fuer die Ausgabe benoetigten Inhalte, Anzeigenamen, Auswahlentscheidungen, Zeitbezuege und Herkunftsnachweise, sodass spaetere Quelldaten- oder Projektionsaenderungen den freigegebenen Stand nicht still veraendern. Ob Entwurf und Pruefstand ebenfalls versioniert werden, entscheidet der Product Owner vor Sprint 7E.

#### Lernentwicklungsgespraech

Ein Lernentwicklungsgespraech ist kein Bericht. Es ist ein eigener paedagogischer Prozess mit:

- Gespraechsvorbereitung
- Gespraechsschwerpunkten
- relevanter Evidenz
- Zielen
- Vereinbarungen
- Gespraechsergebnis

Reine Vorbereitung bleibt fluechtig:

- automatisch zusammengestellte Kompetenz- und Evidenzuebersichten
- Hinweise auf Dokumentationsabdeckung
- moegliche Gespraechsschwerpunkte
- vorlaeufige Auswahl relevanter Beobachtungsbelege

Spaeter speicherbare fachliche Daten koennen sein:

- bewusst festgelegte Gespraechsschwerpunkte oder Agenda
- ausgewaehlte Evidenz als nachvollziehbarer Gespraechsbezug
- gemeinsam oder paedagogisch festgelegte Ziele
- konkrete Vereinbarungen mit Verantwortlichkeit und Zeithorizont
- dokumentiertes Gespraechsergebnis

Die genaue Speichergrenze, Rollen, Datenschutz- und Aufbewahrungsregeln werden erst vor Sprint 7E entschieden. LEG-Daten werden nicht als Berichtsdaten missbraucht und ein Bericht wird nicht zum LEG-Protokoll.

#### PDF und professionelle Ausgabe

PDF ist ein Ausgabeformat und keine Fachschicht. Der PDF-Renderer:

- berechnet nichts
- greift nicht direkt auf SQLite zu
- interpretiert keine Kompetenz-, Evidenz- oder Freigabelogik
- nutzt ausschliesslich eingefrorene Ausgabemodelle

Ein professionelles Ausgabepaket kann Deckblatt, Kompetenzuebersichten, Diagramme, Fachseiten, Lernentwicklung und LEG-Seiten enthalten. Bericht und LEG bleiben darin fachlich getrennte Bestandteile und werden nicht durch den Renderer miteinander vermischt.

#### Grafische Entwicklung

Zulaessige spaetere Grafiken sind insbesondere:

- Kompetenzabdeckung je Fach
- Entwicklungsevidenz ueber Zeit
- Kompetenzbereiche als Balken- oder Liniendiagramm
- Vergleich fachlich passender Zeitpunkte

Grafiken zeigen Dokumentation und Entwicklungsevidenz. Sie duerfen keine algorithmische Leistungsnote, Rangfolge, Prognose oder scheinobjektive Gesamtbewertung erzeugen. Achsen, Legenden, Zeitraum, Datenbasis und fehlende Evidenz muessen nachvollziehbar sein. Die grafische Projektion verwendet dieselbe kanonische Kompetenz- und Evidenzlogik wie Profil, Bericht und LEG.

#### Zielarchitektur

```text
SQLite
-> Repositories
-> kanonische Kompetenzprojektion
-> zeitraumbezogene Evidenzprojektion
-> Bericht-/LEG-Komposition
-> freigegebener Ausgabestand
-> PDF Renderer
```

Keine nachgelagerte Schicht darf Kompetenzstaende neu berechnen oder Beobachtungen fachlich umdeuten. Bericht-/LEG-Komposition waehlt, ordnet und ergaenzt manuell; sie ersetzt weder kanonische Kompetenzlogik noch paedagogische Autorenschaft.

### Historische Produktentscheidung

Der Product Owner gab die beschriebene Zielarchitektur als Leitplanke fuer die Discovery-Sprints 7C und 7D frei. Freigegeben wurde damit die fachliche Trennung von Live-Profil, Berichtsentitaet, LEG-Prozess und PDF-Renderer. Datenbankschema, technische Feldnamen, Persistenz, Statuswechsel, UI und PDF-Implementierung waren zu diesem Zeitpunkt noch nicht freigegeben und wurden erst in den nachfolgenden ADRs entschieden.

Die bestehende Berichtsvorschau bleibt bis zu einer spaeteren Umsetzung eine Live-Arbeitsprojektion. Offizielle Dokumente entstehen erst aus einem explizit geprueften und freigegebenen Ausgabestand. Manuelle paedagogische Texte und Auswahlentscheidungen bleiben in menschlicher Verantwortung.

### Risiken

- Eine Vermischung von Live-Projektion und freigegebenem Stand wuerde alte Berichte nachtraeglich veraendern.
- Eine zweite Kompetenzberechnung in Bericht, LEG oder Diagrammen wuerde widerspruechliche Staende erzeugen.
- Automatisch formulierte Texte koennten als paedagogische Aussage oder Leistungsbewertung missverstanden werden.
- Unklare LEG-Speichergrenzen koennten sensible Gespraechsnotizen ohne fachlichen Zweck oder passende Aufbewahrungsregel dauerhaft speichern.
- Diagramme koennten bei geringer Evidenz, ungeeigneten Zeitvergleichen oder bewertender Farbsemantik eine unzulaessige Objektivitaet suggerieren.
- Historische oder inzwischen inaktive Kompetenzen koennten ohne eingefrorene Anzeigenamen und Herkunftsnachweise im Ausgabestand unlesbar werden.
- PDF-Schriftarten, Seitenumbrueche, Barrierearmut und unterschiedliche Ausgabegeraete koennen die professionelle Reproduzierbarkeit gefaehrden.
- Ungeklaerte Aufbewahrung, Zugriffsschutz und Korrekturregeln fuer freigegebene Ausgaben erzeugen Datenschutz- und Nachvollziehbarkeitsrisiken.

### Urspruengliche Product-Owner-Fragen und aktueller Klaerungsstand

1. **Offen:** Welche Berichtstypen und verbindlichen Berichtszeitraeume werden im ersten Produktumfang unterstuetzt?
2. **Offen:** Wer darf Berichte erstellen, pruefen, freigeben und nach einer Freigabe korrigieren?
3. **Umgesetzt:** Zeitpunkt, Snapshot und Revisionsnachvollziehbarkeit sind fuer Bericht und LEG in ADR-054 und ADR-056 festgelegt.
4. **Teilweise umgesetzt:** Der produktive Berichtspfad und seine Referenzvalidierung sind festgelegt; eine weitergehende fachliche Freigabepolitik fuer offizielle Berichtsinhalte bleibt offen.
5. **Teilweise umgesetzt:** Manuelle Textbereiche und technische Mindestanforderungen sind produktiv vorhanden; verbindliche fachliche Vorlagen und ein abschliessender Pflichtinhaltskatalog bleiben offen.
6. **Teilweise umgesetzt:** Die produktiven neutralen Diagramme und das Verbot automatischer Leistungsdeutung sind festgelegt; eine weitergehende fachliche Kennzahlenpolitik bleibt offen.
7. **Umgesetzt:** Draft-Speichergrenze und Abschluss-Snapshot des LEG sind in ADR-053 und ADR-056 getrennt festgelegt.
8. **Offen:** Duerfen Bericht und LEG in einem gemeinsamen Ausgabepaket erscheinen, und welche klare Trennung sowie Sichtbarkeit gilt je Empfaengerkreis?
9. **Teilweise umgesetzt:** Bericht- und LEG-PDF werden als unveraenderliche Artefakte ihrer Revision gespeichert. Aufbewahrung, Zugriffsschutz, Verschluesselung und betriebliche Archivierung bleiben offen.

### Verbleibende Product-Owner- und Betriebsentscheidungen

- unterstuetzte Berichtstypen und verbindliche Zeitraeume
- Rollen, Berechtigungen, Pruefung und Freigabe
- abschliessende fachliche Vorlagen, Pflichtinhalte und Kennzahlenpolitik
- gemeinsames, weiterhin fachlich getrenntes Bericht-/LEG-Ausgabepaket
- Aufbewahrung, Zugriffsschutz, Verschluesselung und betriebliche Archivierung
- Renderer-Versionierung und mehrere Artefakte pro Revision

### Historische naechste Schritte

Die folgende Reihenfolge dokumentiert den damaligen Planungsstand. Die produktiven Folgeentscheidungen und Umsetzungen sind inzwischen durch ADR-052 bis ADR-057 sowie die zugehoerigen Sprints erfolgt.

1. Sprint 7C erstellt Berichtsvorbereitung und UX-Prototyp als Product Discovery ohne Persistenz. Er prueft Inhaltskomposition, manuelle Autorenschaft, Evidenzauswahl, Statusverstaendnis und ein fachliches PDF-Muster.
2. Sprint 7D erstellt LEG-Konzept und UX-Prototyp ohne Persistenz. Er prueft die Trennung von Vorbereitung, Gespraechsagenda, Zielen, Vereinbarungen und Ergebnis sowie optionale LEG-Ausgabeseiten.
3. Vor Sprint 7E beantwortet der Product Owner die offenen Entscheidungen. Datenmodell-, Architektur-, Datenschutz- und Lifecycle-Review definieren erst dann Entitaeten, technische Namen, Speichergrenzen, Versionierung und Schreibprozesse.
4. Sprint 7E implementiert nur den danach freigegebenen Datenmodell-, Speicherungs- und Versionierungsumfang.
5. Sprint 7F implementiert den PDF-Renderer gegen einen stabilen, eingefrorenen Ausgabe-Contract und validiert Deckblatt, Fachseiten, Diagramme, LEG-Trennung, Seitenumbrueche, Schriftarten und Reproduzierbarkeit.

### Konsequenzen

- Die vorgeschlagene Reihenfolge 7B bis 7F ist fachlich sinnvoll und wird mit den genannten Quality Gates bestaetigt.
- 7C und 7D sind UX-/Discovery-Sprints, keine vorgezogene Persistenz- oder UI-Implementierung.
- 7E darf erst nach Product-Owner-, Datenmodell-, Architektur- und Lifecycle-Freigabe beginnen.
- 7F darf weder SQLite noch Repositories direkt kennen; sein Eingangsvertrag ist das eingefrorene Ausgabemodell.
- `docs/DATA_REGISTRY.md`, `docs/DATA_LIFECYCLE.md`, `docs/TECHNICAL_NAMES.md` und `docs/UI_DATA_MAPPING.md` werden in Sprint 7B nicht um neue Tabellen, Felder, technische Namen, Schreibprozesse oder UI-Felder erweitert.
- Es entstehen in Sprint 7B keine Datenbank-, Migrations-, UI-, Code- oder PDF-Aenderungen.

## ADR-051 - Schnellbeobachtung ohne Kompetenzzuordnung

Status: Umgesetzt

Eine Schnellbeobachtung ist eine bewusst kompetenzfreie aktive Beobachtung mit verpflichtender, nichtleerer Notiz. Sie wird ohne Eintraege in `observation_competency_ratings` gespeichert; ein neues SQLite-Feld ist nicht erforderlich, weil der produktive Schreibprozess Beobachtungen ohne Kompetenzbewertung zuvor nicht zuliess und der Zustand damit eindeutig ist.

Eine spaetere Kompetenzzuordnung und Bewertung ist im normalen Bearbeitungsdialog moeglich. Es erfolgt weder beim Speichern noch spaeter eine automatische Zuordnung oder Bewertung. Sobald eine Kompetenz ergaenzt wird, gelten wieder die normalen Kompetenz- und Bewertungsregeln.

Kompetenzfreie Schnellbeobachtungen erscheinen im Beobachtungsverlauf, wirken mangels Rating-Zeilen aber nicht auf Kompetenzstatus, Dokumentationsfortschritt, Diagramme oder Bestaetigungslogik und erzeugen keine Kompetenz- oder Entwicklungsinformation fuer Berichte.

## ADR-052 - Persistenter Berichtsentwurf ist keine finale Berichtsdomain

Status: Umgesetzt

Sprint 7F.1 fuehrt fuer Lernentwicklungsberichte einen persistenten Arbeitsentwurf mit Status `draft` ein. Der Entwurf speichert manuelle Texte und bewusste Auswahlreferenzen, damit Laura die Berichtswerkstatt schliessen und spaeter weiterbearbeiten kann.

Der Entwurf ist bewusst von einer spaeteren finalen Berichtsentitaet getrennt:

- keine Freigabe oder Pruefung
- keine Versionierung oder Archivierung
- kein eingefrorener Ausgabestand
- keine Signatur oder Empfaengerverwaltung
- keine eigene Kompetenzbewertung

Kompetenzen und Beobachtungen werden ausschliesslich ueber ihre stabilen IDs referenziert. Texte, Hierarchie, Bewertungen, Bestaetigungen, Beobachtungsdatum, Kontext und Notiz bleiben in ihren bestehenden Sources of Truth. Beim Laden werden diese Informationen erneut ueber die kanonische Kompetenz- und Beobachtungsprojektion aufgeloest.

Die persistente Entwurfsstruktur besteht aus `report_drafts` und normalisierten Relationstabellen fuer Faecher/Fachtexte, Kompetenzen, Beobachtungen und Diagramme. Anlegen und Aktualisieren erfolgen atomar ueber ViewModel, Application Layer, Domain-Service und Repository. `ReportOutputModel` und `PdfRenderer` bleiben reine Ausgabeschicht und kennen die Entwurfstabellen nicht.

Eine spaetere Freigabe-, Versions- oder Archivierungsdomain benoetigt eine neue Product-Owner- und Datenmodellentscheidung und darf nicht durch zusaetzliche Statuswerte in diesen Sprint hineingezogen werden.

## ADR-053 - Persistenter LEG-Arbeitsentwurf bleibt eigene Live-referenzierende Domain

Status: Umgesetzt

Offen: fachliche Aufbewahrungsfrist und Rollen-/Berechtigungsmodell

Sprint 7G.1 fuehrt fuer Lernentwicklungsgespraeche einen eigenen persistenten Arbeitsentwurf mit Status `draft` ein. Die Product-Owner-Entscheidung umfasst die manuelle Vorbereitung, die bewusste Auswahl vorhandener Fach-, Kompetenz- und Beobachtungsreferenzen sowie die getrennte Speicherung vorbereiteter und im Gespraech gemeinsam vereinbarter Inhalte.

Der LEG-Entwurf ist weder Lernentwicklungsbericht noch `report_type`, PDF-Dokument, Kopie des Schuelerprofils oder automatische Bewertung. Er verwendet die kanonische Kompetenzstatusprojektion und die vorhandene Beobachtungsprojektion ausschliesslich lesend. Kompetenztexte, Beobachtungsfachdaten, Bewertungen, Bestaetigungen und berechnete Staende werden nicht kopiert oder ueberschrieben.

Der Entwurf referenziert Live-Daten. Er ist deshalb kein eingefrorener Gespraechsstand und besitzt keine finale Version, Freigabe, Archivierung, Signatur oder Historie. Neue Beobachtungsbelege muessen aktiv sein und zum Kind gehoeren. Wird ein bereits referenzierter Beleg spaeter soft-geloescht, bleibt seine ID im Entwurf erhalten und wird beim Laden kontrolliert als nicht verfuegbar ausgewiesen; eine stille Ersetzung ist ausgeschlossen.

Die persistente Struktur traegt den vollstaendigen fachlichen Contract des freigegebenen Prototyps fuer Sprint 7G.2: Gespraechsrahmen, Fach- und uebergreifende Themenauswahl, Kompetenz- und Belegreferenzen, Leitfadeninhalte, getrennte vorbereitete und gemeinsam vereinbarte Ziele/Unterstuetzungen/Vereinbarungen, Zustaendigkeiten, Ueberpruefungszeitpunkt und die drei neutralen Diagrammtypen. Die produktive UI wird erst in Sprint 7G.2 portiert.

Zum Zeitpunkt von Sprint 7G.1 blieben fachliche Aufbewahrungsfrist, Rollen-/Berechtigungsmodell, Uebergang zu einer finalen Gespraechsdokumentation sowie Historisierung gemeinsam vereinbarter Inhalte offen. Uebergang und Historisierung sind inzwischen durch ADR-056 umgesetzt. Aufbewahrungsfrist und Rollen-/Berechtigungsmodell bleiben offen und erweitern den Draft-Status weiterhin nicht.

## ADR-054 - Unveraenderliche Lernentwicklungsbericht-Revisionen

Status: Umgesetzt

Offen: Renderer-Versionierung, Archivierung und Benutzer-/Rollendomain

Sprint 5B.2 setzt die folgenden fuenf Product-Owner-Entscheidungen verbindlich um:

1. Die verantwortliche Lehrkraft darf einen vorhandenen Lernentwicklungsbericht-Draft selbst finalisieren. Gespeichert werden ihr Anzeigename und der Finalisierungszeitpunkt; eine Benutzer-ID oder Rollendomain wird nicht erfunden.
2. Eine Finalisierung benoetigt einen gueltigen Zeitraum, mindestens ein bewusst ausgewaehltes Fach, mindestens einen nichtleeren manuell verantworteten Inhalt und vollstaendig pruefbare Referenzen. Bestaetigte Kompetenzstaende sind keine allgemeine Pflicht.
3. Ein spaeterer LEG-Abschluss enthaelt gemeinsame Vereinbarungen und uebernimmt interne Vorbereitungsnotizen nicht automatisch.
4. Eine Korrektur eines finalisierten Berichts erzeugt eine neue unveraenderliche Revision desselben stabilen Berichtaggregats. Ein neuer LEG-Termin waere dagegen ein neues, getrenntes LEG-Aggregat.
5. Der fachliche Snapshot ist die historische Source of Truth. PDF-Artefakte werden spaeter getrennt modelliert und sind nicht Bestandteil dieser Revisionstabellen.

Der in Sprint 5A dokumentierte Architekturvorschlag bleibt ausdruecklich nicht bindend. Verbindlich sind fuer Sprint 5B.2 ausschliesslich die fuenf vorstehenden Entscheidungen und der hier dokumentierte schmale Berichtspfad; insbesondere wird keine gemeinsame Bericht-/LEG-Basisklasse oder universelle Snapshot-Domain eingefuehrt.

Ein bestehender `RPD` bleibt die bearbeitbare Arbeitsgrundlage und behaelt ausschliesslich den Status `draft`. Bei der ersten bewussten Finalisierung entstehen additiv genau ein stabiles `RPT`-Aggregat und eine unveraenderliche `RPV`-Revision. Weitere Finalisierungen desselben `RPD` verwenden dasselbe `RPT`, setzen die bisher aktuelle Revision innerhalb derselben Transaktion auf `superseded` und erzeugen eine neue `finalized`-Revision mit der naechsten Nummer. Ein Fehler rollt den gesamten Wechsel zurueck.

Mit Revision 1 werden `source_report_draft_id`, `student_id`, `report_type`, `period_start` und `period_end` zur unveraenderlichen Identitaet des `RPT`. Text- und Referenzkorrekturen duerfen weitere Revisionen desselben Aggregats erzeugen. Ein spaeter im `RPD` abweichender Berichtstyp oder Zeitraum darf das vorhandene `RPT` nicht aktualisieren oder umdeuten und blockiert die Folgerevision mit einem Domainfehler. Dafuer ist ein neuer Draft und damit ein neues Berichtaggregat erforderlich.

Der persistierte Snapshot friert den Berichtskontext, sichtbare Schuelerdaten, verantwortlichen Anzeigenamen, manuelle Texte, ausgewaehlte Fachnamen, vollstaendig aufgeloeste Kompetenzen mit Historienkennzeichnung, aktive kind- und fachbezogene Beobachtungsbelege sowie die fachlichen Werte bewusst ausgewaehlter Diagramme ein. Fehlende oder inaktive Beobachtungsreferenzen blockieren die Finalisierung. Bereits gespeicherte, deaktivierte, aber vollstaendig aufloesbare Kompetenzreferenzen duerfen historisch gekennzeichnet eingefroren werden.

Die kanonische Snapshotdarstellung ist UTF-8-JSON mit sortierten Schluesseln, kompakten Trennern, unveraenderten Unicode-Zeichen und ohne nicht endliche Zahlen. Der gespeicherte SHA-256-Hexdigest wird ueber exakt diese gespeicherten Bytes gebildet. `ReportOutputModel` bleibt eine fluechtige Rendererprojektion und ist wegen fehlender stabiler IDs und Provenienz nicht selbst der fachliche Snapshot.

Nicht entschieden oder umgesetzt werden in diesem Sprint UI, finales PDF, Artefakt- und Dateiverwaltung, Renderer-Versionierung, Archivierung, LEG-Abschluss, Benutzer-/Rollendomain oder automatische Bestandsmigration vorhandener Drafts.

Statusfortschreibung: Die UI-Anbindung wurde in Sprint 5B.3, das finale Bericht-PDF in ADR-055 und der getrennte LEG-Abschluss in ADR-056 umgesetzt. Renderer-Versionierung, Archivierung und Benutzer-/Rollendomain bleiben offen.

## ADR-055 - Finales Berichts-PDF ist ein unveraenderliches Artefakt genau einer finalisierten Revision

Status: Umgesetzt

Offen: Renderer-Versionierung, Mehrfachartefakte, Retention, Archivierung und Rollenmodell

Sprint 9A erzeugt ein finales Lernentwicklungsbericht-PDF ausschliesslich aus dem gespeicherten Snapshot einer aktuellen `RPV` mit Status `finalized`. Der Draft, operative Stammdaten, aktuelle Kompetenz- oder Beobachtungsprojektionen und Widgets sind keine Eingangsquellen. Eine `superseded`-Revision bleibt historisch lesbar, darf aber kein neues finales PDF-Artefakt erzeugen.

Der vorhandene reine `PdfRenderer` bleibt einzige PDF-Erzeugung. Der verifizierte `RPV`-Snapshot wird ueber die bestehende renderer-neutrale Revisionsprojektion in dasselbe `ReportOutputModel` adaptiert, das bereits Vorschau und Rendervertrag verbindet. Der Renderer kennt weder SQLite noch Repository, Revisionsstatus, Snapshot-Hash oder Artefaktregeln und berechnet keine Berichtsinhalte.

Pro `RPV` wird hoechstens eine unveraenderliche `LearningReportPdfArtifact`-Referenz mit stabiler `RPA-######`-ID gespeichert. Sie enthaelt relativen verwalteten Pfad, MIME-Type, Dateigroesse, den bei der Erzeugung bestaetigten Snapshot-Hash, SHA-256 der PDF-Bytes und Erzeugungszeitpunkt. Die Datei liegt ohne Klarname unter `data/documents/<student_id>/reports/<RPT>/<RPV>/`. Ein erneuter Aufruf gibt nur ein vorhandenes, auf Pfad und Hash geprueftes Artefakt zurueck und ueberschreibt keine Datei.

Vor dem Rendern werden Revisionsstatus, gespeicherter Snapshot-Hash, Snapshot-Schemaversion, Pflichtstruktur und alle innerhalb des Snapshots referenzierten Faecher, Kompetenzen, Beobachtungen und manuellen Fachtexte validiert. Nach dem Rendern wird der PDF-Hash berechnet; erst danach wird die Artefaktreferenz gespeichert. Scheitert Rendering, Hashing oder Persistenz, entsteht keine gueltige Referenz und eine neu erzeugte Datei wird kontrolliert entfernt.

Eine spaetere neue Fachrevision veraendert weder PDF-Datei noch Hash oder Referenz der vorherigen Revision. Ebenso veraendert eine Draftaenderung kein bestehendes PDF. Nicht Bestandteil von Sprint 9A sind Renderer-Versionierung, Mehrfachartefakte pro Revision, komplexe Archiv- oder Retentionprozesse, LEG-PDF, Benutzerhandbuch und neue Berichtsinhalte.

Statusfortschreibung: Das getrennte LEG-PDF wurde spaeter durch ADR-057 umgesetzt. Die uebrigen genannten Betriebsfragen bleiben offen.

## ADR-056 - LEG-Abschluss als eigenes stabiles Aggregat mit unveraenderlichen Revisionen

Status: Umgesetzt

Offen: Aufbewahrung, Archivierung, Renderer-Versionierung und Rollenmodell

Sprint 10A fuehrt fuer Lernentwicklungsgespraeche einen expliziten Abschluss ein. Der vorhandene `LearningConferenceDraftRecord` (`LCD`) bleibt dabei dauerhaft ein bearbeitbarer, live-referenzierender Entwurf mit Status `draft`. Ein Abschluss aendert, sperrt oder loescht den Draft nicht. Beim ersten erfolgreichen Abschluss entstehen additiv ein stabiles `LearningConferenceRecord` (`LCF`) und eine unveraenderliche `LearningConferenceRevisionRecord` (`LCV`).

LCF und LCV bilden eine eigene LEG-Domain. Berichtsentitaeten `RPD`, `RPT`, `RPV`, ihre Repositories und ihre Application Services werden nicht wiederverwendet. Wiederverwendet wird ausschliesslich das technische Prinzip einer kanonischen UTF-8-JSON-Darstellung mit sortierten Schluesseln, kompakten Trennern, unveraenderten Unicode-Zeichen und SHA-256 ueber exakt die gespeicherten Bytes.

Der Abschluss-Snapshot enthaelt ausschliesslich den reproduzierbaren Gespraechskontext, das Gespraechsdatum, den optionalen Zeitraum, die verantwortliche Lehrkraft, gemeinsam vereinbarte Ziele, Unterstuetzungen und Vereinbarungen, Zustaendigkeiten, den optionalen Ueberpruefungstermin sowie vollstaendig aufgeloeste ausgewaehlte Fach-, Kompetenz- und Beobachtungsreferenzen. Interne Lehrkraftvorbereitung, private Notizen und unfertige Inhalte werden nicht uebernommen. Diagrammdaten sind in Sprint 10A nicht Bestandteil der Abschlussansicht und werden deshalb nicht eingefroren.

Ein Abschluss benoetigt Schuelerbezug, Gespraechsdatum, verantwortliche Lehrkraft und mindestens einen nichtleeren gemeinsamen Ergebnisinhalt aus Ziel, Unterstuetzung oder Vereinbarung. Nicht aufloesbare ausgewaehlte Fach-, Kompetenz- oder Beobachtungsreferenzen sowie inaktive oder fremde Pflichtbelege blockieren den Abschluss. Vollstaendig aufloesbare historische Kompetenzreferenzen duerfen mit Historienkennzeichnung eingefroren werden.

Pro LCD existiert hoechstens ein LCF. Pro LCF existiert hoechstens eine Revision mit Status `completed`. Ein identischer kanonischer Snapshot liefert die vorhandene aktuelle Revision zurueck und erzeugt keine neue Revision. Eine inhaltliche Korrektur erzeugt atomar die naechste LCV; erst innerhalb derselben erfolgreichen Transaktion wird die bisherige Revision auf `superseded` gesetzt. Abgeschlossene Revisionen koennen nicht geloescht oder inhaltlich geaendert werden.

Die historische Lesesicht verwendet ausschliesslich den gespeicherten Snapshot und prueft dessen SHA-256 vor der Projektion. Sie loest keine aktuellen Schueler-, Kompetenz- oder Beobachtungswerte nach und bietet keine Bearbeitung. LEG-PDF, Archivierung, Renderer-Versionierung und eine gemeinsame universelle Bericht-/LEG-Snapshotdomain bleiben ausserhalb von Sprint 10A.

Statusfortschreibung: Das LEG-PDF wurde in ADR-057 separat umgesetzt. Archivierung, Renderer-Versionierung und eine gemeinsame Artefaktdomain bleiben offen beziehungsweise bewusst nicht eingefuehrt.

## ADR-057 - LEG-PDF ist ein unveraenderliches Artefakt genau einer abgeschlossenen LCV

Status: Umgesetzt

Offen: Archivierung, Verschluesselung, Renderer-Versionierung, Mehrfachartefakte und Rollenmodell

Sprint 10B erzeugt ein finales LEG-PDF ausschliesslich aus dem gespeicherten und SHA-256-verifizierten Snapshot einer aktuellen `LearningConferenceRevisionRecord` (`LCV`) mit Status `completed`. LCD, Live-Projektionen, aktuelle Kompetenzaufloesung, aktuelle Beobachtungsdaten und Widgets sind keine Eingangsquellen. Eine `superseded`-Revision bleibt historisch lesbar, darf aber kein neues Artefakt erzeugen.

LCF, LCV und das neue Artefakt bleiben eine eigene LEG-Domain. Berichtsentitaeten `RPD`, `RPT`, `RPV`, `RPA`, Berichtstatus, Bericht-Repositories und Berichtsinhalte werden nicht wiederverwendet. Wiederverwendet werden ausschliesslich der reine `PdfRenderer`, seine renderer-neutralen Ausgabebloecke sowie die technischen Prinzipien fuer verwaltete Pfade, atomare Dateiablage, Dateigroesse und SHA-256-Pruefung.

Pro `LCV` existiert hoechstens eine unveraenderliche `LearningConferencePdfArtifactRecord`-Referenz mit stabiler `LCA-######`-ID. Sie speichert LCV-ID, relativen verwalteten Pfad, MIME-Type, Dateigroesse, bestaetigten Snapshot-Hash, PDF-SHA-256 und Erzeugungszeitpunkt. Die Datei liegt unter `data/documents/<student_id>/learning_conferences/<LCF>/<LCV>/` und enthaelt keinen Schuelerklartext im Dateinamen.

Das PDF enthaelt ausschliesslich abgeschlossene Snapshotinhalte: Schuelerkontext, Gespraechsdatum, verantwortliche Lehrkraft, gemeinsame Ziele, Unterstuetzungen, Vereinbarungen, Zustaendigkeiten sowie bewusst ausgewaehlte Kompetenz- und Beobachtungsbelege. Interne Vorbereitung und nicht abgeschlossene Draftinhalte werden nicht adaptiert. Ein erneuter Erzeugungsaufruf verifiziert ein vorhandenes Artefakt und gibt dieselbe Referenz zurueck; Dateien werden nicht ueberschrieben.

Nicht Bestandteil dieser Entscheidung sind Archivierung, Verschluesselung, Renderer-Versionierung, mehrere Artefakte pro Revision, ein Rollenmodell oder eine gemeinsame Bericht-/LEG-Artefaktdomain.

## ADR-089 - Persistenzereignisse ordnen Bestätigungsfrische; Anhänge verwenden einen recoverbaren Unit-of-Work

Status: Angenommen und umgesetzt

Die vorhandenen sekundengenauen Zeitfelder können Observation- und
Confirmation-Schreibvorgänge innerhalb derselben Sekunde nicht belastbar
ordnen. Fachliche Datumswerte werden deshalb nicht umgedeutet. Eine minimale
append-only Tabelle `persistence_events` erhält eine monotone
`INTEGER PRIMARY KEY`-Sequenz sowie zwingende Operation-, Typ-, Paar-,
Ordnungs-, CHECK- und Foreign-Key-Felder. Es entstehen keine fachlichen
Zusatzfelder und keine allgemeine Indexmigration.

Historische Observation-/Confirmation-Gleichstände werden nicht über IDs,
alphabetische Ordnung oder zufällige Reihenfolge entschieden. Sie projizieren
`confirmation_unknown`, bis eine neue geordnete Observation-Änderung oder
Bestätigung eine eindeutige Sequenz erzeugt. Aktive Evidence und technische
Frische bleiben getrennte Projektionen. Unveränderliche ältere Bericht- und
LEG-Revisionen bleiben unverändert.

Observation, Ratings, Ereignisse und Dokumentreferenzen werden in einer
SQLite-Transaktion geschrieben. Neue Dateibytes werden zuvor unter einem
gemeinsamen kernelgebundenen Writer-Lock kontrolliert gestaged, vollständig
verifiziert und no-clobber publiziert. Ein versioniertes Journal bindet
Operation-Token, Vorher-/Sollzustand, reservierte IDs und Dateievidenz.
SQLite und Dateisystem werden ausdrücklich nicht als gemeinsam atomar
behandelt; Recovery erkennt nur den gebundenen Vorherzustand oder den exakt
committeten Sollzustand und blockiert alle Konflikte.

Das Journal schützt gegen Crash, Partial Write und zufällige Korruption, nicht
gegen aktive Manipulation durch denselben lokalen Benutzer. Journal- und
Stagingbereinigung, ein zusätzlicher Ereignisindex, Verschlüsselungsaktivierung,
Build, Pilotrollout und Release bleiben außerhalb dieser Entscheidung.

Query-Gate am 26.07.2026: Die verbindliche Abfrage
`WHERE student_id = ? ORDER BY event_sequence` verwendet ohne Sekundärindex
erwartungsgemäß `SCAN persistence_events`. Ein synthetischer deutlich
überdimensionierter Bestand mit 100.000 Ereignissen für einen Schüler und 500
Kompetenzen wurde einschließlich Python-Gruppierung in 0,3171 Sekunden
projiziert. Für den realistischen lokalen Pilotbestand ist dies kein kritischer
Scan. Ein möglicher Index auf `(student_id, event_sequence)` bleibt deshalb ein
separater, erneut zu prüfender Vorschlag und wird in P1-Paket 1 nicht angelegt.
