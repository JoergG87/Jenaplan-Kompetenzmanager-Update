# Technical Naming Registry

## Cipher-Produktkomposition

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `CipherProductRuntimeCoordinator` | authentifizierte Composition Root für frischen Cipher-First-Run und vollständigen Restart ohne Migration oder Reparatur | Security Application Composition |
| `CipherProductRuntimeScope` | bindet die bestehenden Security-Foundation-Pfade exakt an die produktiven `RuntimePaths`-Rollen | Security Application Composition |
| `OpenedCipherProductRuntime` | geprüfte gemeinsame keyed Haupt-, Dokument- und Schlüsselruntime zur Injektion in Adapter und Shell | Security Application Composition |
| `CipherProductRuntimeError` | strukturierter sanitisierter Startupfehler mit `CipherProductRuntimeOperation` | Security Application Composition |
| `FinalV4SQLCipherRuntimeScope` | Pfad-/Markergrenze einer Final-V4-SQLCipher-Komposition | Final-V4 SQLCipher Runtime |
| `MarkerGatedFinalV4SQLCipherRuntimeScope` | doppelmarker-gesperrter Foundation-Scope des frischen V4-Produktpfads | Final-V4 SQLCipher Runtime |
| `FinalV3DocumentRuntimeCoordinator` | komponiert Companion und Managed Document Store mit bereits geladener gemeinsamer Database-Key-Runtime | Final-V3 Document Runtime |
| `PILOT_FIRST_RUN_SCHOOL_YEAR_ID` | stabile technische ID für den fachlichen First-Run-Standard `2026/27` dieses Pilotstands | Security Application Composition |
| `prepare_cipher_runtime_storage` | erzeugt nur Root, Export-, Backup- und Logverzeichnisse; keine Klartext-Dokumentablage | Desktop Runtime |
| `CipherBackupRestoreUnavailableError` | blockiert sämtliche ZIP-v1-Backup-/Restore-Einstiege im Cipher-Produktmodus | Desktop Backup/Restore Adapter |
| `FinalV4EncryptedBackupApplicationService` | übersetzt die vorhandene Desktop-Backupaktion ohne Fallback in genau ein `.jkmebackup` | Backup/Restore Application Layer |
| `FinalV4EncryptedRestoreApplicationService` | bindet Vollverifikation, `RESTORE_READY`, Preview, Cipher-Handoff und vorhandenen Live-Worker | Backup/Restore Application Layer |
| `VerifiedCipherSchoolYearTransitionBackupAdapter` | erzeugt das verschlüsselte Pflichtbackup innerhalb der bereits aktiven Schuljahreswechsel-Sperre | School-Year Transition Application Layer |
| `FinalV4BackupRestoreApplicationError` | sanitisierter endnutzergeeigneter Fehlervertrag ohne Pfade, Hashes oder Exceptions | Backup/Restore Application Layer |

Produktive `RuntimePaths`-Rollen sind `key_runtime_metadata`,
`keyset_metadata`, `database_key_envelope_registry`, `final_v4_runtime`,
`final_v4_database`, `document_companion_database`,
`encrypted_document_storage` und `backups`. Sie enthalten keine DMK oder
Database-Key-Materialien.

## Final-V4-Schema-, Startup- und Testnamen

**Status:** Final V4 ist der frische fachliche Pilotvertrag. Die historische
V3-only-Assignmentgrundlage bleibt fachlich erhalten; es gibt keine
V3→V4-Migration. Zentrale Assignment-API, SJ-2E-Umstellung der
produktiven Membership-Reader, SJ-2F-Umstellung der produktiven Writer und
Final-V4-Runtime-Aktivierung, die isolierte synthetische
SJ-3C.2-Ausführung, das anwendungsweite SJ-3C.3-Maintenance-Gate und die
verpflichtende SJ-3C.4-Backupbindung und SJ-3C.5-Passwort-Step-up-Grenze sind
lokal implementiert.

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `FINAL_SCHEMA_VERSION` | einzige unterstützte Produktschemaversion `4` | Core Database Compatibility |
| `FINAL_SCHEMA_FINGERPRINT` | vollständiger kanonischer Fingerprint des direkten finalen Schemas | Core Database Compatibility |
| `FinalV4SchemaInitializer` | Qt-freie direkte Erzeugung und Verifikation einer neuen vollständigen V4-Datenbank; keine Migration | Core SQLite Schema |
| `SyntheticV4SeedBuilder` | ausschließlich testseitige deterministische Befüllung einer frisch erzeugten temporären Final-V4-Datenbank | Test Support |
| `seed_cipher_pilot_test_data` | erweitert den vorhandenen Seed-Workflow über die produktiven Final-V4-Adapter mit ausschließlich synthetischen Fachdaten und verschlüsselten Managed Documents | Pilot Test Support |
| `build_cipher_pilot_test_root` | erzeugt ohne Reset genau einen neuen systemtemporären, same-installation nutzbaren Cipher-Testroot samt Restart-, `.jkmebackup`- und Restore-Staging-Nachweis | Pilot Test Support |
| `JENAPLAN_SQLCIPHER_417_WHEEL` | absoluter Buildinput für das lokal reproduzierte und manifest-hashgebundene SQLCipher-4.17-Wheel; kein Index-Fallback | macOS Build |
| `DatabaseStartupResolver` | read-only Klassifizierung als fehlend, exakt final, unbekannt oder Recovery erforderlich | Core Database Startup |
| `DatabaseStartupCoordinator` | kontrollierte Disposition vor jeder fachlichen Runtime-Vorbereitung | Core Database Startup |
| `DATABASE_NOT_FOUND` | am geprüften Produktpfad existiert keine Datenbankdatei | Core Database Startup |
| `V4_INITIALIZATION_REQUIRED` | eine autorisierte Neuanlage muss direkt Final-V4 erzeugen und anschließend neu prüfen | Core Database Startup |
| `V4_SCHEMA_READY` | exaktes Final-V4 ist vollständig verifiziert und für die normale Runtime zugelassen | Core Database Startup |
| `SCHEMA_UNSUPPORTED` | vorhandenes Schema entspricht nicht exakt dem finalen registrierten Schema | Core Database Startup |
| `RECOVERY_REQUIRED` | unlesbarer, beschädigter, unsicherer oder Restore-seitig nicht abgeschlossener Zustand | Core Database Startup |
| `MaintenanceGate` | zentrale Qt-freie In-Process-Grenze für Writerzulassung, Drain und exklusiven Maintenancebesitz | Core Runtime |
| `MaintenanceState` | ausschließlich `NORMAL`, `MAINTENANCE_PENDING`, `MAINTENANCE_ACTIVE` oder `RECOVERY_REQUIRED` | Core Runtime |
| `WriterLease` | reentrante, genau einmal freizugebende Zulassung eines vor `PENDING` begonnenen Produktwrites | Core Runtime |
| `MaintenanceCapability` | nicht fälschbare In-Process-Besitzberechtigung für genau einen Owner und Maintenancezweck | Core Runtime |
| `MaintenancePurpose` | trennt `SCHOOL_YEAR_TRANSITION` ausdrücklich von `BACKUP_RESTORE` | Core Runtime |
| `MaintenanceGuardedConnection` | gemeinsame produktive Connection-Grenze, die jede schreibende SQLite-Transaktion genau einmal am Gate anmeldet | Core SQLite Runtime |

## Schülerbezogene Dokumentationsfachnamen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `student_documentation_subject_profiles` | Modus `inherit` oder `custom` je stabiler Schüler-/Schuljahridentität | Core SQLite Schema |
| `student_documentation_subject_selections` | exakte normalisierte `subject_id`-Menge eines `custom`-Profils | Core SQLite Schema |
| `DocumentationSubjectMode` | ausschließlich `inherit` oder `custom` | Core Student Subject Domain |
| `StudentDocumentationSubjectConfiguration` | Qt-freie gespeicherte Konfiguration; fehlendes Profil projiziert `inherit` | Core Student Subject Domain |
| `SQLiteStudentDocumentationSubjectRepository` | connection-gebundene Profile-, Auswahl-, Katalog- und Defaultpersistenz ohne Transaktionsbesitz | Core SQLite Persistence |
| `StudentDocumentationSubjectService` | Qt-freie Read-/Write-Transaktionsgrenze für Modus, vollständigen Replace und Resolver | Application Student Subjects |
| `effective_documentation_subjects` | deterministische effektive Fachmenge aus globalem Default oder exakter Custom-Auswahl | Application Student Subjects |
| `DocumentationSubjectWriteStatus` | ausschließlich `changed` oder mutationsfreies `no_change` | Core Student Subject Domain |
| `StudentDocumentationSubjectOptionViewModel` | aktives kanonisches Katalogfach mit stabiler `subject_id` und sichtbarem Label für den Profil-Editor | Desktop Student ViewModel |
| `StudentDocumentationSubjectProjectionViewModel` | schuljahresgebundene Profilprojektion mit Modus, aktivem Katalog, effektiver Auswahl und Read-only-Zustand | Desktop Student ViewModel |
| `StudentDesktopAdapter.save_student_documentation_subjects` | bewusste vollständige `inherit`-/`custom`-Speichergrenze zum bestehenden Application-Service | Desktop Student Adapter |
| `StudentProfileScreen.documentation_subjects_save_requested` | UI-Signal mit stabiler Schüler-/Schuljahridentität, Modus und vollständigem Fach-ID-Draft | Desktop Student Profile |
| `StudentProfileScreen.documentation_subject_summary` | kompakte rein lesende Zusammenfassung aus Modus und Anzahl effektiver Fächer | Desktop Student Profile |
| `StudentProfileScreen.documentation_subject_toggle_button` | lokaler Disclosure-Schalter ohne Persistenzwirkung | Desktop Student Profile |
| `StudentProfileScreen.documentation_subjects_body` | standardmäßig eingeklappter bestehender `inherit`-/`custom`-Editor | Desktop Student Profile |

Nicht mehr registrierte Produktnamen sind
`SchoolYearV2ToV3MigrationEngine`, `VerifiedBackupEvidence`,
`V2_MIGRATION_REQUIRED`, `V2_BOOTSTRAP_READY`,
`V2_READY_FOR_BACKUP`, `V2_READY_FOR_CUTOVER` sowie alle
V2-Klassifikations-, Cutover-Plan-, Failpoint- und
Bootstrap-Transition-Typen.

## Schuljahres- und Assignmentnamen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `SchoolYear` | validiertes Schuljahr mit technischer ID, Label, inklusivem Datumsbereich und Status | Core School-Year Domain |
| `SchoolYearStatus` | ausschließlich `planned`, `current` oder `closed` | Core School-Year Domain |
| `StudentMembershipAssignment` | datiertes inklusives Kurs-/Stammgruppenintervall eines Kindes innerhalb eines Schuljahres | Core Assignment Domain |
| `StudentAssignmentStatus` | ausschließlich `enrolled` oder `exited` | Core Assignment Domain |
| `V3Student` | Schülerstammdaten ohne Membershipfelder: ID, Name, Notiz, Aktiv-/Archivstatus und technische Zeitpunkte | Core Student Domain |
| `AssignmentResolutionStatus` | neutrale eindeutige Auflösung als `ENROLLED`, `EXITED`, `NO_ASSIGNMENT`, `CURRENT_SCHOOL_YEAR_MISSING`, `AMBIGUOUS` oder `STUDENT_ARCHIVED` | Application Assignment Read |
| `AssignmentAtDateProjection` | Qt-freie Zuordnungsprojektion eines Kindes am expliziten fachlichen Datum einschließlich neutralem Status und Accessible Name | Application Assignment Read |
| `CurrentStudentMembershipProjection` | Qt-freie aktuelle Schuljahresprojektion am einmalig vom Aufrufer gesetzten `as_of`-Tag | Application Assignment Read |
| `AssignmentReferenceRequest` | Unveränderlicher Batchauftrag mit genau `request_key`, `student_id` und `reference_date`; bindet eine fachliche Quelle an ihr explizites Referenzdatum, ohne selbst Membership zu behaupten | Application Assignment Read |
| `CurrentMembershipReadSnapshot` | Unveränderliche aktuelle Lesesicht auf genau ein `current`-Schuljahr und genau einen `as_of`-Tag; enthält ausschließlich aktuelle `ENROLLED`-Mitglieder, `CURRENT_SCHOOL_YEAR_MISSING`-/`AMBIGUOUS`-Diagnostik und zentral berechnete Gruppen-, Kurs- und Kursverbundzähler | Application Assignment Read |
| `SchoolYearTransitionPreview` | Vollständige deterministische SJ-3A-Gesamtprojektion aller V3-Kinder mit Zählern, globalen Validierungsissues und `executable`; rein lesend, ohne Aktivierung oder Planpersistenz | Application School-Year Transition Preview |
| `SchoolYearTransitionPreviewItem` | Flüchtiger Vorschlag genau eines Kindes mit bisheriger Zuordnung, unveränderter Stammgruppenvorgabe, ausschließlich aus `courses.year_level` abgeleitetem Kursziel und sichtbaren Warn-/Blockercodes | Application School-Year Transition Preview |
| `SchoolYearTransitionValidationIssue` | Stabil codierter globaler oder kindbezogener Warn-/Blockerzustand der SJ-3A-Vorschau | School-Year Transition Domain |
| `SchoolYearTransitionPreviewService` | Connection-gebundene Qt-freie Read-Komposition aller SJ-3A-Quellen in einem SQLite-Read-Snapshot; setzt `query_only` und führt keine Writes aus | Application School-Year Transition Preview |
| `SchoolYearTransitionPreviewProjector` | SQLite-freier deterministischer Vorschlags- und Validierungsalgorithmus für SJ-3A | Application School-Year Transition Preview |
| `SchoolYearTransitionPreviewViewModel` | Qt-freies SJ-3B-Anzeigemapping des aktuellen flüchtigen Plans mit Validierung, Zählern, sichtbaren Issues, planbasierten Einzeloptionen und kombinierbarer Zeilenfilterung | Desktop ViewModel |
| `SchoolYearTransitionPreviewDialog` | PySide-Dialog zur individuellen und sichtbarkeitsgebundenen Sammelbearbeitung sowie zur finalen geschützten Bestätigung, Phasen-, Ergebnis- und Fehlerprojektion; besitzt keine Backend-Fachlogik | Desktop UI |
| `SchoolYearTransitionDecisionOptionViewModel` | darstellungsfertige bewusste Einzeloption aus den aktiven Kurs-/Gruppenoptionen des flüchtigen Plans; öffnet oder selektiert nichts automatisch | Desktop ViewModel |
| `SchoolYearTransitionPlan` | unveränderlicher rein flüchtiger SJ-3B-Plan aus Preview und expliziten aktiven Kurs-/Gruppenoptionen; jede Einzel- oder Sammelbearbeitung über stabile `student_id`-Identitäten liefert eine neue Instanz | Application School-Year Transition Plan |
| `SchoolYearTransitionPlanItem` | flüchtiger Zielstand genau einer stabilen `student_id` mit Anzeigename, kopierter bisheriger Zuordnung, Zielgruppe/-kurs, Zielstatus, ursprünglichen Issues, Auflösungs- und Bearbeitungskennzeichen | Application School-Year Transition Plan |
| `SchoolYearTransitionPlanTargetStatus` | flüchtiger Zielstatus `ADVANCE_1_TO_2`, `ADVANCE_2_TO_3`, `OTHER_COURSE`, `REPEAT_YEAR_LEVEL_THREE`, `EXITED` oder `UNRESOLVED` | Application School-Year Transition Plan |
| `SchoolYearTransitionCourseDecision` | bewusst protokollierte flüchtige Kursentscheidung oder unveränderter Vorschlag | Application School-Year Transition Plan |
| `SchoolYearTransitionGroupDecision` | bewusst protokollierte flüchtige Stammgruppenentscheidung, insbesondere aktuelle Gruppe beibehalten, Vorschlag behalten oder andere aktive Gruppe wählen | Application School-Year Transition Plan |
| `SchoolYearTransitionPlanValidationIssue` | deterministischer globaler oder kindbezogener Strukturfehler des flüchtigen Plans | Application School-Year Transition Plan |
| `SchoolYearTransitionPlanCounts` | deterministische Zähler ausschließlich aus dem aktuellen flüchtigen Plan | Application School-Year Transition Plan |
| `SchoolYearTransitionPlanValidation` | vollständiges deterministisches Prüfergebnis des flüchtigen Plans ohne Ausführungsfreigabe | Application School-Year Transition Plan |
| `SchoolYearTransitionPlanError` | Ablehnung einer ungültigen flüchtigen Bearbeitungsanforderung ohne Seiteneffekt | Application School-Year Transition Plan |
| `school_year_transition_plan_sha256` | kanonischer SHA-256 ausschließlich über technische Plan-, Entscheidungs- und Quellenwerte; Anzeigenamen und darstellende Kurs-/Gruppennamen sind ausgeschlossen | Application School-Year Transition Execution |
| `SchoolYearTransitionExecutionCounts` | deterministische technische Ergebniszahlen des atomaren Wechsels | Application School-Year Transition Execution |
| `SchoolYearTransitionExecutionResult` | unveränderliche Rückgabe eines neu committed oder idempotent wiedergefundenen Transitionbelegs | Application School-Year Transition Execution |
| `SchoolYearTransitionExecutionError` | fail-closed Ablehnung vor oder innerhalb der atomaren Ausführungsgrenze mit stabilem technischen Code | Application School-Year Transition Execution |
| `ExecuteSchoolYearTransition` | Qt-freier Application-Service für einmaligen Step-up-Verbrauch vor Maintenance-Anforderung, PENDING→ACTIVE-Aktivierung, Writer-Drain, verpflichtendes verifiziertes Backup, erneute Plan-/Quellenprüfung, `BEGIN IMMEDIATE`, atomare Writes, Beleg, Integritätsprüfung, Rollback, kontrollierte Gatefreigabe und optionale private Phasencodes | Application School-Year Transition Execution |
| `SchoolYearTransitionActivationController` | Desktop-eigene QThread-Lifecyclegrenze für genau einen Step-up-/Executor-Lauf mit Doppeltstartschutz und main-thread-sicherem Phasen-, Erfolgs- und Fehlerergebnis | Desktop Composition |
| `SchoolYearTransitionActivationWorker` | widgetfreie Worker-Komposition aus vorhandenem Passwort-Step-up und bestehendem Executor; erzeugt nur flüchtige technische Laufidentitäten | Desktop Composition |
| `SchoolYearTransitionActivationErrorInfo` | credential- und detailfreier Fehlercode für die neutrale UI-Projektion | Desktop Composition |
| `SchoolYearTransitionBackupEvidence` | unveränderlicher SJ-3C.4-Nachweis aus sicherer technischer Backup-ID, echtem Archiv-SHA-256, gebundenem Quellen-SHA-256, Final-V4-Schemafingerprint und zeitzonenbewusstem Verifikationszeitpunkt | Application School-Year Transition Backup |
| `VerifiedSchoolYearTransitionBackupAdapter` | Qt-freie Verbindung zum vorhandenen Backup-Application-Service; blockiert offene Observation-Recovery, erstellt ein normales Backup ohne Recovery-Writes, verifiziert die veröffentlichten Bytes erneut und berechnet Quellen- sowie Schemaidentität aus der isoliert verifizierten Backup-Datenbank selbst | Application School-Year Transition Backup |
| `SchoolYearTransitionStepUpService` | Qt-freie SJ-3C.5-Grenze zur vorhandenen App-Passwortprüfung sowie zur Ausgabe, einmaligen Prüfung und Verwerfung einer flüchtigen plan- und zweckgebundenen Autorisierung | Application School-Year Transition Step-up |
| `SchoolYearTransitionStepUpAuthorization` | nicht persistente, höchstens zwei Minuten gültige Einmal-Autorisierung mit Zweck `SCHOOL_YEAR_TRANSITION`, Erzeugungs-/Ablaufzeitpunkt, technischer ID, Planhash und Verbrauchsstatus; enthält keine UI- oder Credentialdaten | Application School-Year Transition Step-up |
| `SchoolYearTransitionStepUpResult` | credentialfreie Weitergabe des vorhandenen `AuthenticationStatus`, der vorhandenen Drosselungswartezeit und ausschließlich bei Erfolg der Step-up-Autorisierung | Application School-Year Transition Step-up |
| `SchoolYearTransitionStepUpError` | sanitisiertes fail-closed Ergebnis für ungültige, abgelaufene, zweck- oder planfremde und bereits verbrauchte Autorisierung | Application School-Year Transition Step-up |
| `SchoolYearTransitionExecutionRepository` | Connection-gebundene Schreib- und Prüfgrenze innerhalb der vom Application Service besessenen Transaktion; öffnet, committet, rollt nicht zurück und schließt nicht selbst | Core School-Year Transition Persistence |
| `StoredSchoolYearTransition` | unveränderliche technische Projektion eines vorhandenen `school_year_transitions`-Belegs | Core School-Year Transition Persistence |
| `SchoolYearTransitionRepositoryError` | fail-closed Fehlercode der Transition-Schreibgrenze | Core School-Year Transition Persistence |
| `SchoolYearRepository` | Connection-gebundener SQLite-Read auf `school_years`; öffnet und steuert keine Transaktion | Core Assignment Persistence |
| `StudentSchoolYearAssignmentRepository` | Connection-gebundene set-basierte SQLite-Reads und atomar orchestrierbare Writes auf Assignments | Core Assignment Persistence |
| `V3StudentRepository` | Connection-gebundene Persistenz ausschließlich der V3-Schülerstammdaten | Core Student Persistence |
| `SchoolYearAssignmentReadSession` | Connection-gebundene zentrale Assignment-API innerhalb eines vom Aufrufer besessenen SQLite-Read-Snapshots beziehungsweise einer vom Aufrufer besessenen Transaktion; öffnet, committet, rollt nicht zurück und schließt nicht selbst | Application Assignment Read |
| `SchoolYearAssignmentQueryService` | zentrale Qt-freie Datums-, Eindeutigkeits-, Batch- und Statusgrenze; delegiert zusammengesetzte produktive Reads an eine `SchoolYearAssignmentReadSession` | Application Assignment Read |
| `CreateStudentWithInitialEnrollment` | atomare Anlage von V3-Schülerstammdaten und initialem `enrolled`-Assignment | Application Student Lifecycle |
| `UpdateStudentMasterData` | atomare Änderung ausschließlich von Name, Notiz und technischen Stammdatenzeitpunkten | Application Student Lifecycle |
| `EnrollStudent` | atomare Anlage eines expliziten, überschneidungsfreien `enrolled`-Intervalls | Application Assignment Lifecycle |
| `ChangeStudentMembership` | atomare Kürzung und Folgezuordnung eines einzelnen Kindes an einem expliziten Stichtag; unverändertes Ziel liefert `NO_CHANGE` | Application Assignment Lifecycle |
| `ExitStudentFromSchoolYear` | atomare Kürzung und Anlage eines `exited`-Intervalls ohne Gruppe, Kurs oder Archivierung | Application Assignment Lifecycle |
| `ArchiveStudent` | getrennte Stammdatenarchivierung nach fail-closed Prüfung auf aktive Einschreibung am expliziten `as_of`-Tag | Application Student Lifecycle |
| `StudentMembershipChangeDialog` | PySide-Dialog für Vorschau und bewusste Bestätigung genau eines datierten Kurs-/Stammgruppenwechsels eines Kindes | Desktop UI |
| `StudentExitDialog` | PySide-Dialog für den getrennten datierten Austritt eines Kindes aus dem aktuellen Schuljahr | Desktop UI |
| `COURSE_YEAR_LEVEL_REQUIRED_MESSAGE` | sichtbare Validierung für eine fehlende bewusste Kursstufenauswahl | Desktop ViewModel |
| `school_years` | einzige persistierte Schuljahresquelle | Core SQLite Schema |
| `student_school_year_assignments` | einzige persistierte aktuelle und historische Mitgliedschaftsquelle | Core SQLite Schema |
| `school_year_transitions` | unveränderlicher Erfolgsbeleg ausschließlich eines echten Schuljahreswechsels mit vorhandener Ausgangs-ID | Core SQLite Schema |
| `courses.year_level` | stabile fachliche Kursstufe 1, 2 oder 3 | Core SQLite Schema |
| `AssignmentReferenceDate` | vom Aufrufer ausdrücklich übergebener fachlicher Auflösungszeitpunkt | Application Assignment Read |

Ein V3-Schüler besitzt ausschließlich Stammdaten sowie Aktiv-/Archivstatus;
`group_id` und `course_id` sind keine Schülerfelder. Aktuelle und
historische Membershipprojektionen werden aus Assignments gelesen.
Der SJ-2E-Vertrag schließt produktive Reader über
`SchoolYearAssignmentReadSession` an denselben aufrufereigenen Read-Snapshot
wie ihre übrigen Bildschirmprojektionen an; diese Codeumsetzung ist lokal
erfolgt. Ein historisch passendes Assignment bleibt auch für ein später
archiviertes Kind als `ENROLLED` oder `EXITED` auflösbar;
`STUDENT_ARCHIVED` ersetzt keinen historischen Treffer.

SJ-2F verdrahtet die registrierten Student-Lifecycles als produktive
Schreibgrenzen. Ein normaler Stammdatenwrite besitzt keine Kurs-, Gruppen-,
Schuljahres-, Intervall- oder Statusparameter. Einzelwechsel, Austritt und
Archivierung verwenden jeweils ihren eigenen Namen und ihre eigene
Transaktion; ein Mehrkindwechsel oder Schuljahreswechsel ist unter keinem
dieser Namen freigegeben. `SQLiteStudentRepository` bleibt ausschließlich
eine V3-lesende Kompatibilitätsprojektion und besitzt keine produktiven
Schreibmethoden.

Ein `AssignmentReferenceRequest` verwendet für einen Bericht ausschließlich
dessen `period_end`, für ein LEG ausschließlich dessen `conference_date` und
für eine Beobachtung ausschließlich `observations.date`. Ein freies Dokument
ohne fachliches Referenzdatum erzeugt keine Anfrage und bleibt hinsichtlich
der Zuordnung neutral. Weder V2-Schülerfelder noch eine aktuelle oder letzte
bekannte Zuordnung sind Ersatzquellen. `V3_SCHEMA_READY` aktiviert nur die
technische Runtime für die exakte Schemaidentität. Es erzeugt kein Schuljahr
und ändert keinen Reader-, Writer- oder Assignmentvertrag.

`school_year_transitions.from_school_year_id` bezeichnet stets ein wirklich
vorhandenes Ausgangsschuljahr und darf nicht leer sein. Eine initiale
V3-Erzeugung ist kein Transitionstyp und besitzt keinen Beleg.

SJ-3A verwendet das Ende des eindeutigen `current`-Schuljahres als expliziten
Assignment-Stichtag und projiziert ausnahmslos jedes V3-Kind. Stufe 1 wird nur
bei genau einem aktiven Stufe-2-Kurs vorgeschlagen, Stufe 2 entsprechend nur
bei genau einem aktiven Stufe-3-Kurs. Stufe 3, fehlende oder mehrdeutige
Zielkurse sowie nicht eindeutige oder ungültige Ausgangsdaten bleiben
`UNRESOLVED`. Name, Sortierung und Farbe eines Kurses sind keine
Ableitungsquellen. `executable` ist nur bei null ungelösten Items und null
Blockern wahr; SJ-3A besitzt trotzdem keinen Execute- oder Writerpfad.

Versionsnamen anderer Verträge bleiben unberührt: Insbesondere bezeichnen
Backupformat-v1, Security-Store-v2/v3 und kryptografische Formatversionen
keine Datenbankschemaversion.

## LEG-HTML-Produktpfad und isolierter Bericht-HTML-Spike

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `JKM_LEG_UI` | Internes Prozess-Gate mit ausschließlich `qt` oder `html`; fehlt der Wert, bleibt `qt` aktiv | Desktop Composition Root |
| `JKM_REPORT_UI` | Internes Prozess-Gate mit ausschließlich `qt` oder `html`; fehlt der Wert, bleibt `qt` aktiv | Desktop Composition Root |
| `LocalQrcWebEnginePolicy` / `LocalQrcWebEnginePage` | Neutrale interne Security-Basis für lokale `qrc:`-Web-UIs mit blockiertem Netzwerk, externen Navigationen, Popups, Downloads und persistenten Browserdaten | Desktop UI |
| `LearningReportHtmlSession` | Prozesslokale Bindung genau eines bewusst gewählten vollständigen RPD-Drafts an bestehende Report-Adapter- und Application-Service-Callbacks | Desktop UI |
| `LearningReportHtmlBridge` | Explizite Bericht-only-`QWebChannel`-Fassade für vollständigen Python-Draft, Lazy-Evidenz, Save, Finalisierung, read-only RPV-Snapshots und opaque RPA-Aktion; keine generische Invoke-Fläche | Desktop UI |
| `LearningReportHtmlDialog` | Optionaler lokaler QWebEngine-Host der Berichtswerkstatt mit fünf DOM-lokalen Hauptseiten und Python-owned Dirty-/Close-Vertrag | Desktop UI |
| `LearningConferenceHtmlBridge` | Explizite LEG-only-`QWebChannel`-Fassade vor einem vorhandenen Python-Draft und freigegebenen Save-/Completion-/Revisions-/Artifact-Callbacks; kein Adapter-, Repository-, Datei-, Security- oder generischer Command-Zugriff | Desktop UI |
| `LearningConferenceHtmlDialog` | Produktnaher Python-Host mit `QWebEngineView`, eingebetteten `qrc:`-Ressourcen, nicht persistentem Profil, blockierter externer Navigation und Python-owned Dirty-/Close-Vertrag | Desktop UI |
| `LearningConferenceHtmlSession` | Prozesslokale Bindung genau eines vorhandenen Preparation-, Draft-, Revisions- und optionalen LCA-Kontexts an die explizite LEG-Bridge; keine Persistenz und keine neue fachliche Identität | Desktop UI |
| `ReportLegHtmlBridge` / `ReportLegHtmlSpikeHost` / `ReportSpikeSession` / `ConferenceSpikeSession` | Weiterhin ausschließlich isolierte Spike-Namen unter `prototypes/report_leg_html`; keine Produktnavigation | Prototype Desktop UI |

Die beiden Gates autorisieren ausschließlich die jeweilige Oberflächenwahl und
bleiben voneinander unabhängig. Packaging, Pilot und Release werden dadurch
nicht freigegeben.

## Phase 2 Berichte-Übersicht - implementiert

Die folgenden Namen sind für die lokal implementierte Phase-2-Projektion
registriert. Sie ergänzen ausschließlich Lesepfade, flüchtige Projektionen und
UI-Verhalten; es gibt keine neue Persistenz, Tabelle oder Migration.

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `ReportOverviewTimelineEventViewModel` | Flüchtiges displayfertiges Dokumentationsereignis mit vorhandenem Ereignistyp, normalisiertem fachlichem Zeitpunkt, stabiler Quellidentität, neutralem Text und optional vorhandenem Navigationsziel; zulässige Identitäten sind `("observation", observation_id)`, `("report", report_draft_id)`, `("learning_conference", learning_conference_draft_id)` und `("confirmation", student_id, competency_id)`; keine Persistenz und keine pädagogische Bewertung | Desktop ViewModel |
| `ReportOverviewSubjectDocumentationViewModel` | Schuljahresbezogene, je effektiv relevantem Schülerfach deduplizierte Mengen aktueller dokumentierter Kompetenzen, vorhandener Beobachtungen und optionaler neutraler Bestätigungsinformation; ohne Nenner, Prozent- oder Qualitätssemantik | Desktop ViewModel |
| `ReportOverviewProjectionWarningViewModel` | Flüchtiger neutraler Anzeigezustand für unvollständig lesbare Phase-2-Dokumentationsdaten; keine Fehlerkorrektur oder Ersatzannahme | Desktop ViewModel |
| `ReportOverviewViewModel.timeline_events` | Vollständige ausgewählte und deterministisch geordnete Phase-2-Timeline-Liste: alle gültigen Bericht-/LEG-Abschlussereignisse sowie bei weniger als 15 Dokumentereignissen die rein zeitliche Ergänzung bis zum Zielumfang 15; keine Viewport-, Relevanz- oder Prioritätsauswahl | Desktop ViewModel |
| `LearningReportRevisionHistory` | In einem Batch gelesene Bericht-Draft-ID mit allen vorhandenen unveränderlichen Revisionen; Verifikation und Auswahl des neuesten gültigen Stands erfolgen anschließend im bestehenden Domain-Service | Core Report Domain |
| `LearningConferenceRevisionHistory` | In einem Batch gelesene LEG-Draft-ID mit allen vorhandenen unveränderlichen Revisionen; Verifikation und Auswahl des neuesten gültigen Stands erfolgen anschließend im bestehenden Domain-Service | Core LEG Domain |
| `LearningReportRepository.list_revision_histories_for_student` | Schülerbezogener Read für alle Berichtaggregate und Revisionen ohne Abfrage je Revision | Core Report Port |
| `LearningConferenceRepository.list_revision_histories_for_student` | Schülerbezogener Read für alle LEG-Aggregate und Revisionen ohne Abfrage je Revision | Core LEG Port |
| `LearningReportRevisionReadService.verify_revision` | Öffentliche read-only Verifikationsgrenze für eine bereits gelesene Berichtrevision | Application Report Read |
| `LearningConferenceRevisionReadService.verify_revision` | Öffentliche read-only Verifikationsgrenze für eine bereits gelesene LEG-Revision | Application LEG Read |
| `SQLiteStudentDocumentationProjectionRepository.read_batch` | Schülerbezogener Batchread für aktive Beobachtungen, Zuordnungen, aktuelle Kompetenzen, sichere Bestätigungsstände, Fächer und vorhandene Frischeinformation; SJ-2E bindet ihn an die aufrufereigene Connection und denselben konsistenten SQLite-Read-Snapshot wie die Assignment-Session | Core Projection Persistence |
| `ReportTimelineScrollArea` | Ausschließlich darstellungsbezogene horizontale Scrollfläche für die vollständig gelieferte Timeline; verwaltet Wheel-/Tastaturbedienung, nicht aber Auswahl, Ordnung oder Fachlogik | Desktop UI |
| `REPORT_SUBJECT_SYMBOLS` | UI-only Zuordnung kleiner neutraler Fachsymbole zu vorhandenen stabilen `subject_id`; unbekannte Fächer erhalten einen neutralen Punkt, Symbole sind weder Diagramm noch Bewertung | Desktop UI |

Kompetenzzuordnungen `(observation_id, competency_id)` bleiben Grundlage für
Fachkarten, Segmente, Belegdetails, Fachzuordnung und Deduplizierung. Sie
erzeugen keinen eigenen `ReportOverviewTimelineEventViewModel`. Bericht und
LEG verwenden die jeweilige Draft-ID als Aggregatidentität und die neueste
gültige, hashverifizierte Revision ausschließlich als sichtbaren Stand und
Navigationsziel. Das LEG-Timeline-Datum ist `conference_date`;
`completed_at` bleibt technischer Lifecyclezeitpunkt.

`LearningReportSubjectViewModel.current_count` bleibt ein vorhandener
Paket-1-/Berichtvorbereitungsname, ist aber kein Bestandteil des
Phase-2-Fachkartenvertrags. `StudentProfileDashboardViewModel.orientation_changes`
bleibt eine vorhandene Profilprojektion und ist keine
Phase-2-Timeline-Projektion.

## Berichte-Übersicht 0.3.1 / Paket 1

Dieser Abschnitt dokumentiert die historische Paket-1-Basis. Für die sichtbare
Phase-2-Fachkarten- und Timeline-Darstellung gilt der vorstehende
Phase-2-Vertrag.

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `ReportOverviewViewModel` | Displayfertige, nicht persistente Zusammensetzung der getrennt gelesenen Bericht-/LEG-Status-, Zeitraum-, Historien-, Fach- und Aktionsprojektionen | Desktop ViewModel |
| `ReportOverviewActionViewModel` | Konkretes bestehendes Navigationsziel der Übersicht mit interner ID-Bindung und fachlichem sichtbarem Aktionslabel | Desktop ViewModel |
| `ReportStatusCardViewModel` | Statuskarte genau eines eindeutig gewählten RPD oder des leeren beziehungsweise mehrdeutigen Auswahlzustands | Desktop ViewModel |
| `LearningConferenceStatusCardViewModel` | Ausschließlich aus vorhandenen LCD-/LCF-/LCV-Lesesichten gebildete LEG-Statuskarte | Desktop ViewModel |
| `ReportNextStepViewModel` | Konkreter Navigationsverweis auf eine bereits vorhandene Bericht-/LEG-Aktion ohne pädagogische Empfehlung oder automatische Priorisierung | Desktop ViewModel |
| `ReportHistoryItemViewModel` | Gemeinsame read-only Anzeigezeile für getrennt gelesene Bericht- oder LEG-Drafts und -Revisionen | Desktop ViewModel |
| `ReportSubjectEntryViewModel` | Neutrale Fachkachel mit technischem `subject_id`, sichtbarem Fachnamen, bereits kanonischen Dokumentations-/Beobachtungszahlen und vorhandenem Bericht-Sprunganker; keine qualitative Bewertung und kein Kompetenzstatus | Desktop ViewModel |
| `StudentDesktopAdapter.report_overview_for_student` | Einzige Desktop-Kompositionsgrenze für die Paket-1-Übersicht; hält Bericht- und LEG-Application-Queries getrennt | Desktop Adapter |
| `LearningReportDialog.focus_evidence_subject` | Kontrollierte Navigationsgrenze zum bestehenden Bereich `Kompetenzen & Belege`; setzt Fachfilter und sichtbaren Tastaturfokus, übernimmt aber keine Kompetenz | Desktop UI |
| `LearningReportPeriodSelectionDialog` | Nicht persistente Pflichtauswahl von Beginn und Ende vor dem Öffnen eines neuen Berichtsentwurfs; keine fachliche Zeitquelle und keine Kompetenzübernahme | Desktop UI |
| `ReportOverview*` | Objektname-Familie der Paket-1-Karten, Zeitraumprojektion und Fachsprunganker; keine Daten- oder Statusquelle | Desktop UI |
| `_selected_report_draft_ids` / `_selected_learning_conference_draft_ids` | Rein flüchtige Shell-Navigationserinnerung einer ausdrücklich getroffenen Auswahl; keine automatische Wahl und keine Persistenz | Desktop Shell |
| `AppShell.open_learning_report_revision` / `AppShell.open_learning_conference_revision` | Gemeinsame direkte Navigationsgrenzen zu den bestehenden unveränderlichen RPV-/LCV-Leseansichten | Desktop Shell |

## Pilot-Releaseautomation

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `ReleaseConfig` | Validierte kanonische Projektion der ausschließlich nicht geheimen Werte aus `release/release_config.toml`; Stable muss `false` sein | Release Automation |
| `ReleasePilot` | Terminalbasierter Application Service für Inspect, Prepare, Build, Paketprüfung, GitHub, Appcast und öffentliche Verifikation | Release Automation |
| `release-manifest.local.json` | Ignoriertes lokales, atomar geschriebenes Wiederaufnahme- und Assetidentitätsmanifest mit privaten Laufpfaden | Release Automation |
| `release-manifest.json` | Sanitierte Manifestvariante ohne private absolute Pfade oder Secrets | Release Automation |
| `release/release_state.json` | Ignorierter lokaler Zeiger auf den aktuellen Releaselauf; keine fachliche oder Security-Persistenz | Release Automation |
| `PHASES` | Monotone Allowlist `inspected`, `prepared`, `built`, `package_verified`, `github_draft_created`, `github_assets_verified`, `github_published`, `appcast_prepared`, `appcast_published`, `remote_verified` | Release Automation |
| `package_verified` | Alle konfigurierten Gates sind am exakten DMG bestanden; keine Aussage über die vorherige fachliche Gesamtsuite oder reale Hardwareabnahme | Release QA |
| `JENAPLAN_SPARKLE_ROOT` | Ausschließlich lokaler Pfad zur verifizierten Sparkle-Distribution; kein Schlüsselpfad und keine persistierte Konfiguration | Release Operations |
| `--approve-github-publish` | Explizites Orchestratorgate für Tag, Draft und GitHub-Pre-Release | Release Operations |
| `--approve-appcast-publish` | Zusätzliches explizites Gate für Signatur, Pilot-Appcast-Commit und Remoteverifikation | Release Operations |

## P1-Paket 1 - Ereignisordnung und Attachment-Unit-of-Work

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `PersistenceEventRecord` | Append-only Ereigniszeile mit monotoner `event_sequence`, Operation-Bindung, betroffenem Schüler-/Kompetenzpaar und technischer Ordnungssemantik | Core Persistence |
| `PersistenceEventKind` | Allowlist `observation_created`, `observation_updated`, `observation_competency_changed`, `observation_deactivated`, `confirmation_upserted`, `historical_observation_state`, `historical_confirmation_state` | Core Persistence |
| `PersistenceOrderingState` | `ordered`, `unknown` oder `not_applicable`; `unknown` darf nie über die technisch vergebene Sequenz fachlich entschieden werden | Core Persistence |
| `SQLitePersistenceEventRepository` | Append-only Writer und schülerbezogene Read-Projektion der Ereignistabelle | Core Persistence |
| `ObservationPersistenceUnitOfWork` | Qt-freier Gesamtprozess für Observation, Ratings, Anhänge, Ereignisse, Retry und Recovery | Application / Core Persistence |
| `ObservationOperationJournal` | Versioniertes kanonisches Crash-/Retry-Journal unter `.observation-staging/<operation_token>/` | Core Persistence |
| `ObservationWriterLock` | Kernelgebundener exklusiver Advisory Lock auf kontrolliert geöffnetem FD; gemeinsame Sperre für Observation-UoW, Backup und Restore | Core Persistence |
| `ObservationOperationPhase` | Monotone Allowlist `PREPARED`, `FILES_STAGED`, `FILES_PUBLISHED`, `DATABASE_COMMITTED`, `COMPLETE` | Core Persistence |
| `ManagedDocumentStore` | Gemeinsame Qt-freie Portgrenze für geplantes Prepare, Vollverifikation, idempotente Aktivierung/Deaktivierung und kontrolliertes Lesen; wird von Beobachtungsanhängen und allgemeinen verwalteten Schülerdokumenten mit derselben Runtimeinstanz genutzt | Application / Core Persistence |
| `EncryptedObservationAttachmentRuntime` | Kompatibilitätsalias auf `ManagedDocumentStore`; keine zweite Store- oder Securityarchitektur | Application / Core Persistence |
| `ManagedStudentDocumentService` | Journalisierter fachlicher Application-Lifecycle für Create, Replace, Remove, Retry, Restart und kontrolliertes Lesen allgemeiner Schülerdokumente | Application / Documents |
| `.managed-document-staging/<operation_token>/managed-document.json` | Privates technisches Retry-Journal ohne Originalname, Pfad oder Schülerzuordnung; bindet MED-ID, Prepare-Plan, Operation und Payload-Hash | Application / Core Persistence |
| Managed-Document-Phasen | `INTENT`, `REFERENCE_COMMIT_PENDING`, `DATABASE_COMMITTED`, `POINTER_PENDING`, `REFERENCE_COMPENSATION_REQUIRED`, `REFERENCE_COMPENSATED`, `COMPLETE`; jede Vor-Commit-Lücke bleibt restartfähig oder blockiert fail-closed | Application / Core Persistence |
| `operation_token` | Stabiler zufälliger Bezeichner genau eines bewusst ausgelösten schreibenden Gesamtvorgangs; Retry verwendet denselben Wert | Application |
| `operation_payload_hash` | SHA-256 der kanonischen vollständigen Solloperation; bindet Ereignissatz und Recoveryentscheidung | Core Persistence |
| `attachment_intent.storage_mode` | Journalgebundene Allowlist `plaintext` oder `encrypted`; Recovery mit abweichender Runtime blockiert statt zwischen Cipher- und Klartextpfad zu wechseln | Core Persistence |
| `SQLiteObservationRepository._next_observation_id` | Schmaler Read ausschließlich vorhandener `observation_id`-Werte; die Auswahl und das zugehörige Create laufen unter demselben `BEGIN IMMEDIATE` | Core Persistence |
| `confirmation_unknown` | Kanonischer Live-Projektionszustand für nicht beweisbar geordnete historische Observation-/Confirmation-Gleichstände | Desktop Projection |

`ObservationOperationJournal` schützt gegen Crash, Partial Write und zufällige
Korruption. Es ist kein authentisiertes Security-Journal und behauptet keinen
Schutz gegen einen aktiven Manipulator mit denselben lokalen Benutzerrechten.
`MED-######` und `OBS-######` bleiben unverändert; alle nicht abschließend
aufgelösten Journalreservierungen blockieren eine Wiedervergabe.

## Releasebasis 0.3.0 / Build 303

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `create_confirmation_message` | Produktinterne Factory für explizit deutsch beschriftete Bestätigungsaktionen; Abbrechen ist Escape- und Standardaktion | Desktop UI |
| `QLineEdit.inputMethodHints` für Passwortfelder | Qt-Semantik `ImhHiddenText`, `ImhSensitiveData`, `ImhNoAutoUppercase` und `ImhNoPredictiveText`; keine private Cocoa-Bridge oder gespeicherte Eingabe | Desktop UI |
| `should_attempt_startup_device_authentication` | Reine Startentscheidung: automatische Geräteanmeldung nur bei Loginpflicht ohne aktivierte Touch-ID-Präferenz | Desktop Security Coordinator |
| `PYINSTALLER_RESET_ENVIRONMENT` | Öffentliche PyInstaller-Steuerung mit Wert `1` ausschließlich für die neue frozen App-Instanz nach Restore; der Restore-Worker selbst bleibt Worker derselben Instanz | Core Restore Runtime |
| `process_exited_early` | Technischer `restart_handshake.status`, wenn der gestartete App-Prozess vor bestätigtem Startup-Handshake endet | Core Restore Runtime |
| `restart_handshake.exit_code` | Nichtfachlicher Prozess-Exitcode für den frühen Neustartfehler; enthält weder Token noch Kommandozeile | Core Restore Runtime |

Die vorhandene Security-Bridge bleibt ausschließlich Eigentümer von Keychain
und LocalAuthentication. Sie erhält keinen Zugriff auf Qt-Textfelder oder
private Qt-Cocoa-Objekte. Die sichtbare macOS-Passwortvorschlagsannahme bleibt
bis zum realen Test des gebauten Bundles offen.

## SQLCipher 4.17 - isolierte macOS-arm64-Buildbasis

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `build_sqlcipher_4_17_macos_arm64.py` | Erzeugt aus hashgebundenen Quellen in genau einem neuen temporären Root die SQLCipher-4.17-Amalgamation und das lokal markierte arm64-Wheel | Security Build |
| `audit_sqlcipher_4_17_macos_arm64.py` | Vergleicht zwei unabhängige Builds bytegenau und prüft Wheelarchitektur, Linkage, RPATH, Pfadlecks, Lizenzen und das dritte Test-Venv | Packaging QA |
| `smoke_test_sqlcipher_4_17.py` | Prüft im sauberen Venv Version/Provider, verschlüsseltes Reopen, Wrong-Key-/Klartextablehnung und Integrität mit synthetischen Laufzeitkeys | Security Build QA |
| `sqlcipher_4_17_macos_arm64_sources.json` | JSON-Vertrag für Quellen, Toolchain, Flags und erwartete SHA-256 | Security Build |
| `SQLCIPHER_4_17_LOCAL_BINDING_VERSION` | lokal eindeutig markierter abgeleiteter Bindingstand `0.6.2+jkm.sqlcipher4170.1`; kein neuer Importname und keine Produktabhängigkeit | Security Build |
| `SQLCIPHER_4_17_SOURCE_DATE_EPOCH` | fester reproduzierbarer Wheelzeitpunkt `1783468800` für beide unabhängigen Buildroots | Security Build |

## DMK-Database-Key-Runtime - interne technische Namen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `DatabaseKeyRuntime` | Qt-freie, restartfähige Orchestrierung des vorhandenen DMK-/Keyset- und Database-Key-Envelope-Lifecycles; öffnet keine Datenbank | Security Application Layer |
| `DatabaseKeyRuntimeGate` | Read-only Gateauflösung; standardmäßig `DISABLED`, nur bei exaktem Gatewert, privatem System-Temporärroot und festem Marker aktiv | Security Application Layer |
| `DatabaseKeyRuntimePaths` | Feste Rollen für technischen Root, Metadatenroot, Keyset-Sidecar und Envelope-Registry; keine Produkt-`RuntimePaths` | Security Application Layer |
| `LoadedDatabaseKeyRuntime` | Flüchtiges verifiziertes Ergebnis mit DMK-/Database-Key, IDs, Generationen, Context und nicht geheimen Fingerprints; Secretfelder sind repr-geschützt | Security Application Layer |
| `DatabaseKeyRuntimeDecision` | Strukturierte technische Projektion `DISABLED`, `ACTIVE` oder `BLOCKED` samt sanitiertem Fehlercode, Operation und Retryfähigkeit | Security Application Layer |
| `DatabaseKeyRuntimeError` | Sanitierter fail-closed Runtimefehler ohne Secret oder lokalen Pfad | Security Application Layer |
| `DataKeysetRuntimePhase` | Nicht geheime Publishkette `prepared -> dmk_published -> database_key_generation_started -> envelope_published -> database_key_active -> active` | Security Domain |
| `JKM_DMK_DATABASE_KEY_RUNTIME_TEST` | Internes Gate; ausschließlich der exakte Wert `1` aktiviert die weitere Rootprüfung | Security Test Gate |
| `JKM_DMK_DATABASE_KEY_RUNTIME_ROOT` | Expliziter absoluter markergebundener privater Testroot unter der System-Temporärwurzel | Security Test Gate |
| `.jkm-dmk-database-key-runtime-test-root` | Fester nicht geheimer Marker für den ausschließlich technischen Testroot | Security Test Gate |
| `security-key-runtime-v1` | Privates `0700`-Verzeichnis ausschließlich für Keyset- und Envelope-Metadaten | Security Infrastructure |
| `dmk_database_key_runtime_worker.py` | Separater Testprozess für First Run, Restart und reales namespacetes Keychain-Cleanup | Security Test QA |

## Final-V4-SQLCipher-Runtime - interne technische Namen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `FinalV4SQLCipherRuntimeGate` | zusätzliche read-only Gateauflösung auf dem vorhandenen privaten DMK-Testroot; verlangt exakten Gatewert und zweiten festen Marker | Security Application Layer |
| `FinalV4SQLCipherRuntimeCoordinator` | Qt-freie fail-closed Verbindung aus bestätigter Authentifizierung, bestehender DMK-/Database-Key-Runtime, SQLCipher 4.17 und direktem Final-V4 | Security Application Layer |
| `FinalV4SQLCipherConnectionFactory` | feste Pfad-, Provider- und Database-Key-Bindung für Schema, Inspektion, `SQLiteDatabase`, Repositories und Adapter | Core Persistence / Security Runtime |
| `KeyedFinalV4CompatibilityInspector` | mutationsfreie Prüfung einer bereits keyed geöffneten Connection auf Cipher, SQLite, Integrität, FK, `user_version` und Final-V4-Fingerprint | Core Database Compatibility |
| `OpenedFinalV4SQLCipherRuntime` | flüchtiges verifiziertes Ergebnis mit derselben schlüsselgebundenen `SQLiteDatabase` für nachgelagerte Application-Schichten | Security Application Layer |
| `SQLCIPHER_4_17_BINDING_VERSION` | exaktes lokales Binding `0.6.2+jkm.sqlcipher4170.1` | Core Persistence |
| `SQLCIPHER_4_17_ENGINE_VERSION` | exakte Engine `4.17.0 community` | Core Persistence |
| `SQLCIPHER_4_17_SQLITE_VERSION` | exakte eingebettete SQLite-Version `3.53.3` | Core Persistence |
| `JKM_FINAL_V4_SQLCIPHER_RUNTIME_TEST` | zusätzliches, standardmäßig inaktives internes Gate; nur exakter Wert `1` setzt die Marker-/Rootprüfung fort | Security Test Gate |
| `.jkm-final-v4-sqlcipher-runtime-test-root` | zweiter fester nicht geheimer Marker auf dem bereits DMK-markergebundenen privaten System-Temporärroot | Security Test Gate |
| `final-v4-sqlcipher-runtime-v1/final-v4.sqlcipher` | feste SQLCipher-4.17-Hauptdatenbank mit exaktem Final-V4 | Security Runtime |
| `final_v4_sqlcipher_runtime_worker.py` | separater Anwendungssmoke- und Abrissprozess für keyed Restart, stabile Fach-IDs sowie echte `os._exit`-Crashgrenzen | Security Test QA |

## Final-V3-Dokumentcontainer-Runtime - interne technische Namen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `FinalV3DocumentSchemaV1` | Exaktes SQLCipher-Companion-Schema v1 für technische Dokumentpointer und unveränderliche Generationen; bindet Installation und Database-Context | Document Persistence / Security Runtime |
| `FinalV3DocumentRuntime` | Qt-freie Operationen `prepare`, `activate`, `read` und `replace` ohne Export, Vorschau oder Produktintegration | Application / Documents |
| `FinalV3DocumentConnectionFactory` | Eigene strikt pfad- und Database-Key-gebundene SQLCipher-Factory für `documents-v1.sqlcipher` | Core Persistence / Security Runtime |
| `FinalV3DocumentRuntimePaths` | Historisch benannter Companion-v1-Vertrag mit Pfadrollen unter dem aktuellen Final-V4-Hauptruntime-Root | Security Runtime |
| `FinalV3DocumentGeneration` | Sanitierte technische Projektion aus Document-/Key-Generation, opaque Storage-ID, Envelope-/Formatnachweisen, Größen, Hash, MIME und Lifecycle | Document Persistence |
| `FinalV3DocumentPreparePlan` | Vor dem Containerwrite journalisierbare Bindung aus fachlicher MED-ID, vorheriger aktiver Generation, erwarteter Zielgeneration und zufälliger opaque Storage-ID | Document Persistence / Observation UoW |
| `FinalV3DocumentRuntime.plan_prepare` / `verify_prepared` | Read-only Planung vor Quellenzugriff und exakte Vollverifikation einer bereits journalgebundenen `PREPARED`-Generation für Retry/Restart | Application / Documents |
| `FinalV3DocumentRuntime.prepare_bytes` | Bereitet eine unveränderliche Dokumentgeneration direkt aus bereits gerenderten binären Memory-Daten vor; erzeugt keine Klartextquelldatei | Application / Documents |
| `ManagedPdfArtifactLifecycle` | Gemeinsamer Qt-freier journalisierter Lifecycle für ausschließlich finale RPA-/LCA-PDF-Artefakte zwischen Memory-Renderer, fachlicher Artefaktreferenz und demselben `ManagedDocumentStore` | Application / Documents |
| `managed-document:<UUID>` | Strikt typisierte interne Referenz im vorhandenen RPA-/LCA-Referenzfeld auf eine getrennte opaque Managed-Document-ID; niemals physischer Pfad oder Storage-ID | Document Persistence |
| `StudentDesktopAdapter.read_learning_report_pdf_artifact` / `read_learning_conference_pdf_artifact` | Technische read-only Auflösung der bestehenden fachlichen Artefakt-ID in vollständig verifizierte PDF-Bytes für einen injizierten Consumer | Desktop Adapter / Documents |
| `FinalV3DocumentRuntime.apply_journaled_changes` | Idempotente atomare Companion-Transaktion für journalgebundene Aktivierungen und Deaktivierungen von Beobachtungsanhängen oder allgemeinen Schülerdokumenten; keine partiellen Pointerzielstände | Application / Documents |
| `FinalV3DocumentRuntime.deactivate` | Idempotente fachliche Pointerdeaktivierung; aktive Generation wird `RETAINED`, physischer Container bleibt bestehen | Application / Documents |
| `StudentDesktopAdapter.read_encrypted_observation_attachment` | Qt-freie Adapterlesenaht MED-ID → aktive fachliche Beobachtungsreferenz → verifizierter Runtime-Consumer | Desktop Adapter / Documents |
| `StudentDesktopAdapter.read_managed_student_document` | Qt-freie Adapterlesenaht MED-ID → aktive allgemeine Fachreferenz → verifizierter Runtime-Consumer; kein Klartextziel und keine OS-Öffnung | Desktop Adapter / Documents |
| `StudentDocumentViewModel.managed_encrypted` | Vom Adapter gesetzte reine Aktionsprojektion für allgemeine Cipher-Dokumente; erlaubt Ersetzen/Entfernen und unterdrückt OS-Öffnung | Desktop Projection |
| `AppShell.student_adapter` | Explizite Composition-Injektion eines bereits keyed Adapters; im Cipher-Produktmodus verpflichtend, historischer Gate-Off-Fallback nur außerhalb dieses Modus | Desktop Composition |
| `FINAL_V3_DOCUMENT_SCHEMA_FINGERPRINT` | Vollständige registrierte Strukturidentität des Companion-Schemas v1 | Core Database Compatibility / Security Runtime |
| `final_v3_documents.active_generation` | Atomarer SQLCipher-Pointer auf genau eine aktive Generation eines bereits aktivierten technischen Dokuments | Document Persistence |
| `final_v3_document_generations` | Historische Generationen mit `PREPARED`, `ACTIVE`, `RETAINED` oder `QUARANTINED`; kein physisches GC | Document Persistence |
| `final_v3_document_runtime_worker.py` | Echter `os._exit`-Nachweis für sieben Container-/Persistenz-/Pointergrenzen im transaktionalen Runtime-Modell; exakte SQLCipher-Komposition separat | Security Test QA |

## Verschlüsseltes Final-V4-Pilotbackup - interne technische Namen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `FinalV4EncryptedBackupService` | Qt-freier Orchestrator aus geöffnetem Gate- oder ADR-101-Produktbestand für Writer-Lock, keyed Snapshots, Dokumentinventar, `.jkmebackup`, Vollverifikation und Restore-Staging | Application / Security Backup |
| `FinalV4EncryptedBackupManifestV1` | Striktes verschlüsseltes V4-Crossbinding von Contexts, Generationen, DB-Rollen, Engine-/Schemaversionen, Größen, Hashes und Dokumentinventar | Security Backup Domain |
| `FinalV4BackupArtifactV1` | Manifesteintrag für Haupt-DB, Companion-DB, Keyset-Metadaten oder Database-Key-Envelope-Registry | Security Backup Domain |
| `FinalV4BackupDocumentV1` | Manifestbindung genau einer registrierten `.jkmedoc`-Generation einschließlich Lifecycle, Key-/Envelope-Generation, Größe und SHA-256 | Security Backup Domain |
| `SQLiteDataKeysetRepository.create_snapshot` | Konsistenter no-clobber SQLite-Backup-Snapshot der nicht geheimen Keyset-Metadaten einschließlich WAL | Security Infrastructure |
| `.jkmebackup` | Ausschließliches verschlüsseltes Backupformat des frischen Gate-On-Final-V4-Piloten | Security Backup |
| `RESTORE_READY` | Gefsyncter Abschlussbeleg im neuen privaten Staging-Root nach vollständigem keyed Reopen und Crossbinding | Security Restore Staging |
| `same-installation encrypted restore` | Restoregrenze mit vorhandenem passenden DMK im lokalen Keychain; kein Gerätewechsel-/DMK-Recovery | Security Governance |
| `FinalV4RestoreReadyVerification` | Ergebnis der wiederholbaren kanonischen READY-, Manifest-, Keyset-, Envelope-, SQLCipher-, Container- und Crossbindingprüfung | Security Restore |
| `FinalV4EncryptedSafetyBackup` | Vollständig verifiziertes `.jkmebackup` plus bis zur Workerübergabe gehaltener Maintenance-Freeze | Security Restore |
| `FinalV4EncryptedRestoreHandoffService` | Erzeugt und konsumiert den einmaligen DMK-authentisierten Cipher-Handoff im vorhandenen Restore-Journalbereich | Security Restore |
| `FinalV4EncryptedLiveRestoreService` | Cipher-Strategie des vorhandenen `ProductiveRestoreService` für Preflight, gemeinsame Vier-Rollen-Einheit, keyed Reopen und Rollback | Security Restore / Core Restore |
| `build_final_v4_restore_verifier` | Technische read-only 4.17-Verifier-Komposition aus bestehendem DMK-/Envelope-Kontext und ADR-101-Pfadscope; öffnet keine Produktdatenbankkomposition | Security Restore Recovery |
| `_read_active_keyset_wal_aware_readonly` | Bootstrap-interner SQLite-Read-only-Snapshot des exakt aktiven Keysets einschließlich bereits committed WAL; ohne Provisionierung oder Lifecycle-Fortschreibung | Security Restore Recovery |
| `classify_terminal_final_v4_restore_artifacts` | strukturelle fail-closed Zulassung ausschließlich terminaler Cipher-Handoff-/Journalbereiche vor dem normalen Product-Open | Security Restore Recovery |
| `validate_terminal_final_v4_restore_evidence` | DMK-HMAC-Prüfung terminaler Cipher-Handoffs nach regulärem bestehendem Key-Load | Security Restore Recovery |
| `classify_active_final_v4_restore_artifacts` | strukturelle Zulassung exakt einer benannten aktiven Cipher-Transaktion nur für ihren Worker nach Parent-EOF; übrige Evidenz muss terminal sein | Security Restore Worker |
| `validate_active_final_v4_restore_evidence` | erneute DMK-HMAC-Prüfung der benannten aktiven Worker-Transaktion und aller retained terminalen Handoffs | Security Restore Worker |
| `active_restore_id` | eng gebundene ADR-101-Kompositionsausnahme für genau den bereits DMK-authentisierten Worker nach Parent-EOF; im normalen App-Start immer `None` | Security Restore Worker / Cipher Composition |
| `recover_interrupted_final_v4_restore` | Restartfähige Prüfung genau eines offenen Cipher-Journals mit Resume, vollständigem Rollback oder `manual_recovery_required` | Security Restore Recovery |
| `final_v4_encrypted_same_installation` | Persistierter `restore_kind` für den ausschließlich gegateten Cipher-Workerpfad | Security Restore |
| `final_v4_live_restore_handoff/v1` | Eigene DMK-HKDF-/HMAC-Domäne für Handoffauthentisierung ohne Schlüssel- oder Sitzungsbytes | Security Cryptography |
| `key_runtime_metadata` | Journalisierte Swap-Rolle für `security-key-runtime-v1/` mit Keyset und Database-Key-Envelope-Registry | Security Restore |
| `final_v4_main_database` | Journalisierte Swap-Rolle der keyed Final-V4-Hauptdatenbank | Security Restore |
| `document_companion_database` | Journalisierte Swap-Rolle der keyed Dokument-Companion-DB | Security Restore |
| `managed_document_storage` | Journalisierte Swap-Rolle des vollständigen verschlüsselten `.jkmedoc`-Bestands | Security Restore |
| `encrypted-restore-safety/` | Retained Zielbereich für das zwingende verschlüsselte Pre-Swap-Sicherheitsbackup | Security Restore |
| `encrypted-restore-staging/` | Gebundener same-filesystem Bereich für bereits vollständig verifizierte `RESTORE_READY`-Bestände | Security Restore |
| `--restore-mode final_v4_encrypted` | Expliziter lazy Worker-Dispatch; der argumentlose Default bleibt `zip_v1` | Desktop Restore Worker |
| `--final-v4-restore-confirm` | Bootstrap-Restart-Handshake im frischen normalen App-Prozess vor `completed`; danach Fortsetzung über Security/Auth und ADR-101-Produktstartup, ohne Backup-/Restore-UI zu aktivieren | Desktop Startup / Security Restore |

## Security Sprint 12 - Release-Hardening und Paketabnahme

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `PACKAGED_SECURITY_INTEGRATION_ARGUMENT` | Historischer Sprint-11-Testeinstieg `--packaged-security-integration-test`; im Final-V4-Pilotbundle weder geroutet noch enthalten | Security Packaging |
| `PackagedSecurityIntegrationSmoke` | Historischer Qt-freier Sprint-11-Testablauf; bleibt als Quelltest erhalten, ist aber aus dem Final-V4-Pilotbundle ausgeschlossen | Security Packaging |
| `PACKAGED_KEYCHAIN_SMOKE_ARGUMENT` | Interner gefrorener Testeinstieg `--packaged-keychain-smoke` für einen isolierten realen macOS-Keychain-Lifecycle | Security Packaging |
| `PackagedKeychainSmoke` | Marker- und Temporärroot-gebundene DMK-Provisionierung, Reopen-, Passwortwechsel-, Fehler- und Cleanup-Prüfung ohne Produktdaten | Security Packaging |
| `PACKAGED_RUNTIME_AUDIT_ARGUMENT` | Interner gefrorener Testeinstieg `--packaged-runtime-audit` für die tatsächlich gebündelte SQLCipher-Bindung, SQLCipher-/SQLite-Version, CommonCrypto-Provider und Cipher-Integrität | Security Packaging |
| `PACKAGED_SMOKE_ARGUMENT` | Interner gefrorener Final-V4-Testeinstieg `--packaged-smoke-test` mit den Modi `initialize`, `restart`, `restore-worker` und `cleanup`; verwendet ausschließlich einen privaten systemtemporären Smoke-Root | Security Packaging |
| `PACKAGED_CIPHER_SEED_ARGUMENT` | Interner gefrorener Testeinstieg `--packaged-cipher-seed` für genau einen neuen privaten systemtemporären Final-V4-Cipher-Testbestand ohne Reset oder Überschreiben | Security Packaging |
| `PACKAGED_CIPHER_SEED_VERIFY_ARGUMENT` | Separater gefrorener Reopen-Einstieg `--packaged-cipher-seed-verify` zur Bestätigung des vorhandenen synthetischen Testbestands, `.jkmebackup` und `RESTORE_READY` | Security Packaging |
| `verify_cipher_pilot_test_root` | Read-only Reopen-Verifikation eines bereits erzeugten synthetischen Cipher-Pilot-Testroots über produktive Keychain-, DMK-, Database-Key-, SQLCipher-, Backup- und Restore-Staging-Grenzen | Test Data / Security Packaging |
| `JENAPLAN_MACOS_BUILD_ROOT` | Optionales absolutes internes Buildziel ausschließlich unter freigegebener Build- oder System-Temporärwurzel | Packaging |
| `JENAPLAN_MACOS_DIST_ROOT` | Optionales absolutes internes Distributionsziel ausschließlich unter freigegebener Dist- oder System-Temporärwurzel | Packaging |
| `audit_macos_security_runtime.py` | Prüft gepinnte Python-/Krypto-/Qt-/SQLCipher-Laufzeiten und arm64-Verfügbarkeit vor PyInstaller | Packaging QA |
| `thin_macos_bundle_arm64.py` | Entfernt vor Codesign alle nicht-arm64-Slices aus Mach-O-Dateien des internen Bundles | Packaging QA |
| `audit_macos_app_bundle.py` | Prüft Bundlemetadaten, alle Mach-O-Dateien auf arm64-only, native Abhängigkeiten/RPATHs, exakte SQLCipher-4.17-Laufzeit mit CommonCrypto, Fachvignetten, Lizenzen sowie verbotene Artefakte, Prototypen und lokale Pfade | Packaging QA |
| `APP_INFO_VERSION` | Sichtbare read-only Projektion `Version <APP_VERSION> · Build <APP_BUILD_VERSION>` im bestehenden Über-Dialog | Desktop UI |

## Security Sprint 11 - kontrollierte Testintegration

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `JKM_SECURITY_INTEGRATION_TEST` | Internes, standardmäßig inaktives Gate; ausschließlich der exakte Wert `1` kann zusammen mit einem gültigen markergebundenen Test-Root aktivieren | Security Integration |
| `SecurityIntegrationGate` | Rein technische Gate- und Test-Root-Prüfung; unbekannte Werte, fehlende Marker, Symlinks, unprivate Roots und Nicht-Temporärpfade blockieren | Security Integration |
| `SecurityIntegrationPaths` | Feste Rollen für Klartextquelle, byte-identische Sicherung, SQLCipher-Ziel, Dokument-Storage, Export, verschlüsseltes Backup, Restore-Staging, Journal und externen Replay-Anker | Security Integration |
| `SecurityIntegrationConnectionFactory` | Einzige Datenbank-Öffnungsgrenze des aktivierten Testpfads; Engine und Key sind explizit, bestehende SQLCipher-Dateien werden ohne Create-/SQLite-Fallback geöffnet | Core Persistence / Security Integration |
| `SQLiteReadOnlyConnectionProvider` | Zentrale Core-Persistence-Grenze für existierende SQLite-Quellen mit `mode=ro`, `immutable=1` und `query_only`; keine Erzeugung und kein Security-Layer-Treiberimport | Core Persistence |
| `SQLITE_RUNTIME_VERSION` | Vom Core bereitgestellte technische SQLite-Laufzeitversion für verschlüsselte Backup-Metadaten; kein Datenbank- oder Gatezustand | Core Persistence |
| `SecurityIntegrationSchemaV1` | Nur im SQLCipher-Testziel vorhandene, über `user_version=1101` eindeutig erkennbare Schemaerweiterung für unveränderliche Dokumentgenerationen und Integrationsmetadaten | Core Persistence |
| `EncryptedDocumentGenerationRecord` | SQLCipher-Datensatz für Document-ID, opaque Storage-ID, Dokument-/Key-Generation, Envelope-Revision, Containerformat, Klartextgröße/-hash, MIME-Typ, Lifecycle und Retained-/Quarantänegrund | Document Persistence |
| `SecurityDocumentApplicationAdapter` | Qt-freier Adapter für vorbereiteten verschlüsselten Import, atomare Pointer-Umschaltung, kontrolliertes Lesen, bewussten Export, Austausch und konservatives Retained-Verhalten | Application / Documents |
| `SecurityEncryptedBackupAdapter` | Gate-gebundener Adapter zwischen SQLCipher-/Dokumentinventar und dem Sprint-9-Container; verifiziert vor Erfolg und stellt nur in einen neuen Staging-Root wieder her | Application / Backup |
| `SecurityIntegrationJournalV1` | Kanonisches HMAC-geschütztes Write-ahead-Journal mit Phasen, Revision, Artefakt- und Dokumentplan sowie sanitisierten Fehlercodes | Security Integration |
| `SecurityIntegrationReplayAnchorV1` | Vom Integrationsroot getrennte committed/pending HMAC-Autorität für monotone Journalrevision und -digest | Security Infrastructure |
| `SecurityIntegrationPhase` | Allowlist `PREFLIGHT`, `BACKUP_VERIFIED`, `DATABASE_MIGRATED`, `DOCUMENTS_PREPARED`, `REFERENCES_SWITCHED`, `ENCRYPTED_BACKUP_VERIFIED`, `REOPEN_VERIFIED`, `COMPLETED`, `BLOCKED`, `RECOVERY_REQUIRED` | Security Domain |
| `SecurityIntegrationOrchestrator` | Gate-gebundene, restartfähige Ablaufsteuerung für eine markierte Klartext-Testinstallation; keine Produktmigration und keine UI | Application / Security Integration |
| `SecurityIntegrationRuntime` | Qt-freie, frisch geöffnete Application-Service-Komposition gegen den vollständig validierten SQLCipher-Bestand | Application |

## Vereinfachte Verschlüsselungsarchitektur nach ADR-088

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `DocumentWrappingKey` | Vom Database- und Backup-Zweck getrennter Wrapping-Key für zufällige Document-Keys | Core Security |
| `DocumentKey` | Zufälliger Schlüssel genau eines versionierten Dokumentcontainers; ausschließlich geschützt im Envelope | Core Security |
| `EncryptedDocumentContainer` | Geplanter versionierter authentifizierter Streaming-AEAD-Container für PDF, Bild, Anhang oder Bericht | Core Security / Documents |
| `DocumentContainerContextV1` | Extern eingebrachter stabiler Installations-, Datenbank- und Dokumentkontext für HKDF, Envelope-AAD und Öffnungsprüfung; kein Produktpfad | Core Security |
| `DocumentKeyEnvelopeV1` | Eigenes strikt versioniertes AES-256-GCM-Envelope für genau einen zufälligen Document-Key; integriert im Ein-Datei-Container, aber vom unveränderlichen Payload-Binding getrennt | Core Security |
| `EncryptedDocumentManifestV1` | Kanonisches ausschließlich verschlüsseltes Manifest mit Dokument-/Storage-Identität, Generationen, Originalname, MIME-Typ, Größe, SHA-256, Chunkanzahl, Erstellungszeit und technischer App-/Formatversion | Core Security / Documents |
| `SyntheticEncryptedDocumentServiceV1` | Injizierter Writer, Header-Inspector, Verifier, sequenzieller Reader, bewusster Export-, Rewrap-, Austausch- und Inventarprototyp ausschließlich für synthetische Sprint-10-Daten | Security Prototype |
| `SYNTHETIC_DOCUMENT_TEST_ROOT_MARKER` | Feste Markerdatei, die zusammen mit Eigentümer-, Modus-, Unterverzeichnis- und Synthetikquellprüfung den Sprint-10-Test-Root mechanisch begrenzt | Security Prototype |
| `DocumentStorageState` | Technische Lifecycle-Allowlist `ACTIVE`, `PREPARED`, `RETAINED`, `QUARANTINED`, `GC_ELIGIBLE`; keine Produkt- oder UI-Projektion | Security Prototype |
| `SyntheticEncryptedDocumentWriterV1` | Streamender No-Clobber-Writer über gebundene synthetische Quelle, versteckte Retained-Datei, `fsync`, vollständige Neu-Verifikation und Hardlink-Publikation | Security Prototype |
| `SyntheticEncryptedDocumentVerifierV1` | Schreibfreie Header-, Envelope-, Kontext-, Manifest-, Chunk-, Hash-, Größen-, Final-, EOF- und Dateiidentitätsprüfung | Security Prototype |
| `SyntheticEncryptedDocumentReaderV1` | Kontrollierter zweiphasiger Reader: vollständige Vorabverifikation, danach sequenzielle zweite Entschlüsselung mit Erfolg erst nach Final-/EOF-/Hash-Prüfung | Security Prototype |
| `SyntheticEncryptedDocumentExportV1` | Bewusster Testexport in einen neuen markergebundenen Root über exklusives no-follow-Tempziel, vollständige Vorab- und Abschlussverifikation, atomaren No-Clobber-Rename sowie descriptor-gebundenes Leeren eigener unvollständiger Ausgabe bei normalen Fehlern | Security Prototype |
| `SyntheticDocumentKeyRewrapV1` | No-Clobber-Neuverpackung desselben Document-Keys unter neuem DMK/Envelope-Revision bei unverändert kopiertem Ciphertext; niemals in-place | Security Prototype |

`EncryptedDocumentContainer`, `DocumentContainerContextV1`,
`DocumentKeyEnvelopeV1`, `EncryptedDocumentManifestV1`,
`SyntheticEncryptedDocumentServiceV1`,
`SyntheticEncryptedDocumentWriterV1`,
`SyntheticEncryptedDocumentVerifierV1`,
`SyntheticEncryptedDocumentReaderV1`,
`SyntheticEncryptedDocumentExportV1` und
`SyntheticDocumentKeyRewrapV1` gehören ausschließlich zum isolierten
synthetischen Security-Sprint-10-Pfad und sind nicht produktiv adressiert.
`AppInstanceLock` bleibt ein registrierter Zielname und ist nicht produktiv
aktiviert.


## Security Sprint 9 - isolierte technische Namen

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `EncryptedBackupContainer` | Versionierter authentifizierter Secretstream-Container für synthetische Backupdaten; keine Produktaktivierung | Core Security / Backup |
| `BackupContainerContextV1` | stabile Installations- und Datenbankkontext-IDs für HKDF- und Envelope-Bindung | Core Security |
| `BackupKeyEnvelopeV1` | AES-256-GCM-Envelope eines zufälligen Backup-Keys unter einem getrennten Backup-Wrapping-Key | Core Security |
| `EncryptedBackupManifestV1` | ausschließlich verschlüsseltes Manifest mit Rollen, Reihenfolge, Größen, Hashes und Chunkanzahl | Core Security / Backup |
| `SyntheticEncryptedBackupServiceV1` | injizierter Writer/Verifier/Restore-Service nur für synthetische Sprint-9-Daten | Security Prototype |
| `SYNTHETIC_BACKUP_TEST_ROOT_MARKER` | feste Markerdatei zur Begrenzung des privaten synthetischen Test-Roots | Security Prototype |

## Security Sprint 8 - vereinfachte Migrationsarchitektur

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `SimplifiedMigrationArtifactV2` | VFS-freie gebundene Source-, Backup- oder Target-Dateirolle mit sicherem relativen Namen, Geräte-/Dateiidentität, Größe und SHA-256 | Security Domain |
| `SimplifiedMigrationCrossbindingV2` | Versionierter VFS-freier Kontext für Root, feste Rollen, Schlüsselgenerationen, Journal, Replay-Anker, Lockkopf und erwartete Engine-/Schemaversionen | Security Domain |
| `SimplifiedMigrationPreflightV2` | Reine read-only Ableitung `NEW`, `RESUME`, `RECOVERY`, `COMPLETED`, `BLOCKED` aus authentisiertem Kontext und phasengerechter Evidenz | Security Domain |
| `SimplifiedMigrationRecoveryDecision` | Allowlist `SAFE_RESTART`, `REPEAT_VALIDATION`, `QUARANTINE_TARGET`, `CONFIRM_BACKUP_AUTHORITATIVE`, `MANUAL_REVIEW_REQUIRED`, `BLOCKED` | Security Domain |
| `AuthenticatedMigrationJournalV2` | Kanonisches HMAC-authentisiertes Journal mit fester Rollenbindung und monotoner Revision | Security Infrastructure |
| `ExternalReplayAnchorV2` | Injizierter committed/pending Replay-Anker außerhalb des Migrationsroots | Security Port / Test Infrastructure |
| `SyntheticMigrationOrchestratorV2` | Ausschließlich per Dependency Injection verdrahteter Orchestrator für einen synthetischen privaten Testroot ohne Produktaktivierung | Security Prototype |
| `SimulatedAtomicExchangePlanV2` | Isolierter Testplan für den simulierten Austausch mit Neustartprüfung und retained Vorgänger | Security Prototype |

Diese Namen sind ausschließlich im isolierten Security-Sprint-8-Pfad
implementiert. Sie importieren weder Identity-VFS noch RuntimePaths und
aktivieren keinen Produkt-, Startup-, Login-, UI- oder Backup/Restore-Pfad.

## Security Sprint 7B - Migration State Foundations

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `MigrationCrossbindingContext` | Kanonischer Kontext aller Sicherheits-, Artefakt- und Versionsbindungen | Security Domain |
| `MigrationArtifactBinding` | Capability- und Identitätsbindung einer Rolle `source`, `backup` oder `target` | Security Domain |
| `lock_binding_digest_sha256` | Nicht zirkulärer Digest aller Kontextfelder außer Lockzustand | Security Domain |
| `LockTransitionType` | Allowlist der sechs Locktransitionen | Security Domain |
| `AuthenticatedLockTransition` | Kanonischer HMAC-Eintrag mit Sequenz, Vorgänger, Kontext, Owner und Evidenz | Security Domain |
| `AuthenticatedLockTransitionChain` | Verifizierbare append-only Transitionen samt Head-Digest | Security Domain |
| `AppendOnlyLockTransitionRepository` | Per-entry und fsync-gebundene Lockpersistenz ohne Produktpfad | Security Infrastructure |
| `AuthenticatedSourceAbsence` | Adapter-authentisierter Abwesenheitsbeleg | Security Domain |
| `AuthenticatedReplayAnchorProjection` | Authentisierte Replay-Anker-Projektion | Security Domain |
| `AuthenticatedEnvelopeRegistryProjection` | Authentisierte Envelope-/Registry-Projektion | Security Domain |
| `AuthenticatedJournalProjection` | Journalprojektion mit Quelldigest und Projektions-Seal | Security Domain |
| `AuthenticatedLockHeadProjection` | Projektion des HMAC-verifizierten vollständigen Lockkopfs | Security Domain |
| `AuthenticatedArtifactProjection` | Capability-authentisierte Soll-/Ist-Projektion der Dateirollen | Security Domain |
| `AuthenticatedMigrationPreflightProjection` | Gemeinsame read-only Preflight-Eingabe | Security Domain |
| `MigrationPreflightMode` | Allowlist `NEW`, `RESUME`, `RECOVERY`, `COMPLETED`, `BLOCKED` | Security Domain |
| `derive_migration_preflight` | Deterministische Modusableitung aus crossgebundenen Projektionen | Security Domain |

Diese Namen begründen keine Produkt-, UI-, Startup- oder
Orchestratorintegration.

## Security Sprint 6 - Replay-Anker, Migrations-Lock und Prototype-Recovery

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `SecurityAnchorState` | Strikt versionierter, nicht geheimer Zustand aus Installation/Security-Context, Anchor-Revision, Database-/DMK-/Keyset-Bindung sowie committed und optional exakt pending Registry-/Journal-Snapshot | Security Domain |
| `committed` | Zuletzt vollständig akzeptierter Anchor-Snapshot mit Database-Context, DMK-/Keyset-ID/-Generation, Registry-High-Water-Mark, Journal-/Migrationsgeneration und exakten Registry-/Journal-SHA-256-Digests | Security Domain |
| `pending` | Optionaler vorbereiteter neuer Snapshot, der den alten committed Stand und exakt geplante neue Digests bindet; kein freier Zwischenstand | Security Domain |
| `registry_sha256` | SHA-256 der exakt authentisierten kanonischen Registry-Datei | Security Domain |
| `journal_sha256` | SHA-256 der exakt authentisierten kanonischen Journaldatei | Security Domain |
| `SecurityAnchorStatus` | Fail-closed Statusallowlist des monotonen Ankers einschließlich aktiv und dauerhaft blockiert | Security Domain |
| `SecurityAnchorError` | Strukturierter Anchor-Fehler ohne Schlüssel, Payload, Pfad oder fachliche Daten | Security Domain |
| `MonotonicSecurityAnchorStore` | Plattformport für Initialisieren, idempotentes Lesen, Vergleichen, Verifizieren, monotones Prepare/Advance, Digest-exakten Commit, monotones Abort und Blockieren | Security Port |
| `abort_pending(expected, observed_committed)` | Monotone Crashauflösung ausschließlich für exakt den weiterhin beobachteten committed Dateistand; entfernt pending, übernimmt dessen höhere Anchor-Revision und setzt weder Artifact-Snapshot noch Revision zurück | Security Port |
| `InMemoryMonotonicSecurityAnchorStore` | Deterministischer, threadsicherer Fake für plattformneutrale Replay-, Parallelitäts- und Windows-Vertragstests | Security Test |
| `MacOSMonotonicSecurityAnchorStore` | Isolierter Keychain-Adapter ohne Datei-Fallback und ohne stille Neuerzeugung bei vorhandenem Security-Bestand | Security Infrastructure |
| `UnsupportedMonotonicSecurityAnchorStore` | Fail-closed Plattformadapter ohne produktive Implementierung, insbesondere für den noch offenen Windows-Pfad | Security Infrastructure |
| `de.jenaplan.kompetenzmanager.monotonic-security-anchor` | Eigener macOS-Keychain-Service für den nicht geheimen, aber vertrauensgebundenen Anchor-Zustand | Security Infrastructure |
| `MigrationLockOwner` | Strikte Eigentümerbindung aus Installation, Database-Context, Migration-ID, PID, Prozessstartidentität, Nonce, Zeitpunkten und SHA-256 der Rootbindung | Security Domain |
| `MigrationLockInspection` | Nicht mutierende Projektion eines verifizierten, fremden, stale, manipulierten oder uneindeutigen Locks | Security Domain |
| `MigrationLockStatus` | Allowlist der Lock-Prüfzustände | Security Domain |
| `MigrationLockError` | Strukturierter fail-closed Lockfehler ohne Secret- oder Fachdateninhalt | Security Domain |
| `MigrationLockPort` | Plattformneutraler Lockvertrag für `acquire`, `verify_owner`, `release` und nicht mutierendes `inspect` | Security Port |
| `ExclusiveMigrationLock` | POSIX/macOS-Prototyp für exklusives Acquire, Eigentumsprüfung, Inspect, kontrollierte Stale-Übernahme und Release; serialisiert Anchor-Prepare/Publish/Commit pro Datenbankkontext prozessübergreifend | Security Infrastructure |
| `InMemoryMigrationLock` | Threadsicherer, eigentümergebundener Fake für deterministische Konkurrenz-, Fremd-Release- und Portvertragstests ohne Dateisystem | Security Test |
| `UnsupportedMigrationLock` | Fail-closed Adapter für Plattformen ohne geprüftes Lock-Backend; jede mutierende Operation liefert `migration_lock_platform_unsupported` | Security Infrastructure |
| `database-migration-v1.lock` | Exklusiv angelegte technische Lockdatei im injizierten synthetischen Test-Root; kein Schlüssel und keine Fachdaten | Security Infrastructure |
| `.recovery-<role>-<migration_id>.quarantine` | Retained Quarantine für ein exakt evidence-gebundenes eigenes Testziel beziehungsweise Backup; Recovery verschiebt per atomarem No-Clobber-Rename, verifiziert die Identität erneut und löscht den Bestand nicht | Security Prototype |
| `PrototypeMigrationRecoveryOrchestrator` | Ausführende Recovery ausschließlich für identitätsgebundene Artefakte des guarded synthetischen Prototyps | Security Prototype |
| `RecoveryExecutionResult` | Sanitisiertes Ergebnis aus vorheriger/nachheriger Journalphase, ausgeführten technischen Schritten und allowlistetem Blockiercode; enthält keine Pfade, Payloads oder Secrets | Security Prototype |
| `src/security/monotonic_anchor.py` | Qt-freie Anchor-Domain und Portvertrag | Security Domain / Port |
| `src/security/infrastructure/monotonic_anchor_store.py` | Plattform- und Testadapter des monotonen Ankers | Security Infrastructure |
| `src/security/migration_lock.py` | Qt-freier Lockvertrag und POSIX/macOS-Prototyp | Security Infrastructure |
| `prototypes/database_encryption_migration/recovery.py` | Isolierte ausführende Recovery-Orchestrierung ohne Produktimport | Security Prototype |

Keiner dieser Namen führt eine `RuntimePaths`-Adresse, UI-, Startup-, Login-,
Auth-Recovery-Code-, Support-Reset-, Backup/Restore- oder Produktintegration
ein. `Recovery` in diesen Namen bedeutet ausschließlich technische
Migrations-Recovery im synthetischen Test-Root.

## Security Sprint 5 - Product-Key-Envelope und Migrationsjournal

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `DatabaseKey` | Flüchtiger zufälliger 32-Byte-Key mit UUID und monotoner Generation; kein Passwort und kein DMK | Security Domain |
| `DatabaseKeyEnvelope` | Striktes kanonisches AES-256-GCM-Envelope v1 für genau einen `DatabaseKey` | Security Domain |
| `DatabaseKeyEnvelopeStatus` | Allowlist `pending`, `active`, `revoked`, `failed` | Security Domain |
| `DatabaseKeyEnvelopeService` | Qt-freier Lifecycle für Erzeugen, Aktivieren, Laden, Widerrufen, Fehlschlagen und terminale Metadatenbereinigung | Security Application |
| `derive_database_wrapping_key` | HKDF-SHA-256-Ableitung mit Database-Kontext, Key-Generation und Rewrap-Revision | Security Domain |
| `DATABASE_KEY_WRAP_PURPOSE` | Feste Domain `jenaplan-kompetenzmanager/database-key-wrap/v1` | Security Domain |
| `DATABASE_KEY_REGISTRY_AUTH_PURPOSE` | Getrennte HMAC-Domain `jenaplan-kompetenzmanager/database-key-registry-auth/v1` | Security Domain |
| `rewrap_revision` | Monotoner Envelope-Zähler, der pro Status-Rewrap einen anderen AEAD-Key-Kontext erzwingt | Security Domain |
| `FileDatabaseKeyEnvelopeRepository` | Atomare HMAC-authentifizierte Sidecar-Registry mit stabilem Database-Kontext und dauerhaftem Generations-High-Water-Mark | Security Infrastructure |
| `database-key-envelopes-v1.json` | Ausschließlich geschützte Envelopes plus öffentliche Registry-Bindung; kein Klartextschlüssel | Security Infrastructure |
| `MigrationJournalState` | Versionierter technischer Zustand mit vollständiger Transition-Historie, Prüfbelegen und Envelope-Cross-Binding | Security Domain |
| `MigrationPhase` | Explizite Allowlist aller vorbereiteten Migrations-, Rollback- und Terminalphasen | Security Domain |
| `MigrationRecoveryEvaluator` | Reine, nicht mutierende, fail-closed Recovery-Entscheidung | Security Domain |
| `AuthenticatedMigrationJournalRepository` | HMAC-authentisierte kanonische und atomare Journalpersistenz | Security Infrastructure |
| `database-migration-journal-v1.json` | Technisches Journal ohne Schlüssel, Passwörter, Schülerdaten, Inhalte oder Klartext-SQL | Security Infrastructure |
| `MIGRATION_JOURNAL_AUTH_PURPOSE` | Feste Domain `jenaplan-kompetenzmanager/migration-journal-auth/v1` | Security Domain |
| `SecureMigrationPrototypeEngine` | Einzige Sprint-5-Integration; ausschließlich guarded synthetischer Sprint-4-Prototyp | Security Prototype |

Diese Namen führen keine RuntimePaths-Adresse, Produktdatenquelle, UI,
Startup-/Login-Kopplung, produktive Migration oder Verschlüsselungsaktivierung
ein.

## Security Sprint 4 - isolierter Migrationsprototyp

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `MigrationPrototypeEngine` | Qt-freie Orchestrierung ausschließlich für guarded synthetische SQLite-zu-SQLCipher-Läufe | Security Prototype |
| `MigrationPaths` | Vier explizite Pfade im selben isolierten Prototyp-Arbeitsbereich: Root, Quelle, Backup, Ziel; offizieller Runner und Tests verwenden einen temporären Root | Security Prototype |
| `FailurePoint` | Testinjektion `backup`, `export`, `commit`, `corrupt_target`, `wrong_key` oder `interrupt_export` | Security Test |
| `DatabaseSnapshot` | Generische technische Struktur- und Wertprojektion für den Vergleich | Security Prototype |
| `ValidationResult` | Gleichheitsnachweis für Tabellen, Rows, PK/FK, Trigger, Views, Indizes, PRAGMAs und Hashes | Security Prototype |
| `MigrationReport` | Sanitisiertes Laufresultat mit Validierung, Größen, Zeitmessung und unverändertem Quellhash | Security Prototype |
| `SyntheticScale` | Ausschließlich synthetische Mengensteuerung einschließlich großer Fixture | Security Test |
| `create_synthetic_source` | Erzeugt die dreifach markierte synthetische Quelle mit 11 repräsentativen Tabellen | Security Test |
| `__jkm_security_sprint_4_synthetic_guard` | Technische Stop-Guard-Tabelle; keine produktive oder fachliche Tabelle | Security Test |
| `simulate_atomic_exchange` | Nicht mutierende Beschreibung eines späteren atomaren Austauschs | Security Prototype |
| `scripts/run_database_encryption_migration_prototype.py` | Flüchtiger Standard-/Großlauf mit Laufzeitkey und JSON-Messprotokoll | Security Test |

`Database Key` bezeichnet einen zufälligen 256-Bit-Schlüssel pro fachlicher
Datenbank. `Database Wrapping Key` bezeichnet den später zweckgebunden aus dem
DMK abgeleiteten flüchtigen KEK. Beide Namen sind Architekturbegriffe; Wrapping
und produktive Persistenz werden in Security Sprint 4 nicht implementiert.

## Security Sprint 3 - Isolierte SQLCipher-Infrastruktur

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `DatabaseEngine` | Explizite Engine-Auswahl `sqlite` oder `sqlcipher`; keine Umgebungsumschaltung | Core Infrastructure |
| `DEFAULT_DATABASE_ENGINE` | Unveränderter Standard `sqlite` | Core Infrastructure |
| `DatabaseConnectionProvider` | Kleiner Qt-freier Verbindungsport für isolierte Engine-Aufrufe | Core Infrastructure |
| `SQLiteConnectionProvider` | Standardbibliothek-Provider mit `sqlite3.Row` und `foreign_keys=ON`; normale Repository-Verbindungen delegieren bei unverändertem Verhalten an ihn | Core Infrastructure |
| `SQLCipherConnectionProvider` | Optionaler fail-closed Provider für neue oder bestehende verschlüsselte Testdatenbanken | Core Infrastructure |
| `SQLCIPHER_SPIKE_BINDING_VERSION` | Für den isolierten Spike gepinntes Python-Binding `sqlcipher3` 0.6.2 | Build / Security Infrastructure |
| `SQLCIPHER_SPIKE_ENGINE_VERSION` | Im Spike nachgewiesene Engine `4.12.0 community`; keine Produktfreigabe | Build / Security Infrastructure |
| `SQLCIPHER_PRODUCT_TARGET_VERSION` | Kontrollierter späterer Build gegen SQLCipher 4.17.0; offenes Release-Gate | Build / Security Infrastructure |
| `DatabaseEngineError` | Basisklasse mit ausschließlich sanitisiertem Fehlercode | Core Infrastructure |
| `SQLCipherUnavailableError` | Binding oder native SQLCipher-Engine fehlt | Core Infrastructure |
| `SQLCipherVersionError` | Geladene Cipher-Version entspricht nicht der expliziten Erwartung | Core Infrastructure |
| `DatabaseKeyMissingError` | Kein Schlüsselmaterial übergeben | Core Infrastructure |
| `DatabaseKeyInvalidError` | Schlüsselmaterial besitzt nicht das freigegebene 32-Byte-Format | Core Infrastructure |
| `DatabaseKeyRejectedError` | Verschlüsselter Header kann mit dem Schlüssel nicht authentisiert/gelesen werden; umfasst technisch ununterscheidbare Headerkorruption | Core Infrastructure |
| `DatabaseCorruptError` | Datei ist strukturell unmöglich oder nach erfolgreichem Keying schlägt Cipher-/SQLite-Integrität fehl | Core Infrastructure |
| `DatabaseFormatUnsupportedError` | Eine Datei mit Standard-SQLite-Klartextheader wurde an SQLCipher übergeben | Core Infrastructure |
| `DatabaseEngineConfigurationError` | Pfad, Modus, Treibervertrag oder Engine-Konfiguration ist ungültig | Core Infrastructure |
| `scripts/smoke_test_sqlcipher_engine.py` | Isolierter technischer Smoke mit Laufzeitschlüssel und synthetischen Daten | Test / Packaging |

Regel: Diese Namen führen keine fachliche Entität, Tabelle, UI-Projektion,
RuntimePaths-Erweiterung, Migration oder Produktaktivierung ein.

## Security Sprint 2 - Key Foundation und DMK

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `DataKeyset` | Ausschließlich Key-ID, Generation, Lifecycle-Status und SHA-256-Fingerprint | Security Domain |
| `DataKeysetStatus` | `pending`, `active`, `revoked`, `failed` | Security Domain |
| `LoadedDataMasterKey` | Flüchtiger 32-Byte-DMK mit Key-ID und Generation; Secret aus `repr` ausgeschlossen | Security Domain |
| `DataMasterKeyService` | Qt-freie Orchestrierung von Erzeugung, Wiederanlauf, Laden, Prüfung, Widerruf und Lösch-Retry | Security Application |
| `DataKeysetRepository` | Port für ausschließlich technische Keyset-Metadaten | Security Port |
| `DataMasterKeyStore` | Plattformport für geheimes DMK-Material; macOS Keychain und spätere Windows-DPAPI-Implementierung | Security Port |
| `SQLiteDataKeysetRepository` | Isolierter Development-Sidecar v1; keine Erweiterung oder Migration von `security.sqlite` | Security Infrastructure |
| `MacOSDataMasterKeyStore` | Keychain-Adapter im eigenen DMK-Namespace | Security Infrastructure |
| `UnsupportedDataMasterKeyStore` | Fail-closed Portadapter ohne Plattformimplementierung | Security Infrastructure |
| `KeyEnvelope` | Kanonisches Format für bereits geschütztes Schlüsselmaterial | Security Domain |
| `KEY_ENVELOPE_FORMAT_VERSION` | Envelope-Version 1 | Security Domain |
| `DATA_MASTER_KEY_BYTES` | Exakt 32 Bytes / 256 Bit | Security Domain |
| `DATA_MASTER_KEY_PURPOSE` | Fester Zweck `data_master_key` | Security Domain |
| `DATA_MASTER_KEY_ALGORITHM` | Erzeugungsalgorithmus `random-256` | Security Domain |
| `DataMasterKeyStoreStatus` | `success`, `not_found`, `unsupported`, `access_denied`, `corrupt`, `error` | Security Domain |
| `de.jenaplan.kompetenzmanager.data-master-key` | Getrennter, nicht mit Gerätecredentials geteilter macOS-Keychain-Service | Security Infrastructure |

## Sprint 0.2S.1 - Support-Assistent UX

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `SupportAssistantApplicationService` | Qt-freie Orchestrierung von Requestprüfung, externer Schlüsselpaarprüfung und unveränderter Tokenerzeugung | Support Application |
| `SupportAssistantError` | Strukturierter fail-closed Bedienfehler ohne Secret- oder Payloaddetails | Support Application |
| `SupportProductKey` | Strikt geprüfter öffentlicher Schlüsselwert des eigenständigen Assistenten | Support Application |
| `SupportRequestProjection` | Datenschutzarme sichtbare Projektion einer kanonisch geprüften Reset-Anfrage | Support Application |
| `SupportKeyProjection` | Sichtbare Public-Key-Projektion aus der freigegebenen Produktregistry | Support Application |
| `LoadedSupportRequest` | Flüchtige Verbindung aus unveränderten kanonischen Bytes, Core-Request und sichtbarer Projektion | Support Application |
| `GeneratedResetCode` | Flüchtiges Ergebnis aus Token, Ablauf, Request-ID und Key-ID; keine Persistenz | Support Application |
| `support_request_reference` | Nicht sicherheitsrelevante Referenz `JKM-<NAME>-<4 ZIFFERN>` aus flüchtigem Installationsnamen und Request-ID | Support Application |
| `SupportAssistantAuditLog` | Append-only JSONL-Audit mit Zeitpunkt, Request-ID, Key-ID und Aktion | Support Infrastructure |
| `SupportAssistantWindow` | Eigenständiger PySide-Schrittfluss für Öffnen, Prüfen, Signieren und bewusste Ausgabe | Support UI |
| `SUPPORT_ASSISTANT_PRODUCT_KEY` | Im separaten Bundle eingebettete öffentliche 1:1-Projektion des freigegebenen `support-2026-b`; Gleichheit zur Produktregistry wird getestet | Support Packaging / Security Review |
| `Jenaplan Support-Assistent.app` | Eigenständige macOS-arm64-Betreiberanwendung ohne Zugriff auf Produkt-Runtime | Packaging |
| `Jenaplan-Support-Assistent-0.2.2-macOS-arm64.zip` | Separates Supportpaket mit App, Anleitung, Version und Prüfsummen | Packaging |
| `scripts/build_macos_support_assistant.sh` | Separater arm64-Build, Bundleprüfung und Paketaufruf | Packaging |
| `scripts/build_support_assistant_package.py` | Feste Paketanlage sowie Secret-, Daten- und Pfadscan | Packaging |

Installationsname, sichtbarer Benutzername und Anfragecode erweitern weder
`SupportResetRequest` noch `SupportResetPayload`. Protokollversion, Feldlisten,
Nonce, Signaturbytes und UUID-Bindung bleiben unverändert.

## Sprint 0.2U.1 - Sicherer macOS-Updatepfad

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `Sparkle.framework` | Gepinnter nativer Updatekern für macOS; kein Eigentümer fachlicher Daten | Packaging / macOS Infrastructure |
| `MacOSUpdateService` | Geplanter Qt-freier Application-Port für Prüfung, Status und sicheren Installationsaufschub | Application |
| `SparkleUpdateAdapter` | Geplanter Infrastructure-Adapter über kleine Objective-C++-/C-ABI-Bridge | Infrastructure macOS |
| `pilot` | Fester beaufsichtigter Appcast-Kanal; nicht durch Lehrkräfte editierbar | Release-Betrieb |
| `stable` | Getrennter späterer Standardkanal ohne automatische Übernahme von Pilotinstallationen | Release-Betrieb |
| `APP_BUILD_VERSION` | Geplante monotone technische `CFBundleVersion`, getrennt von der sichtbaren SemVer-Produktversion | Packaging |
| `Einstellungen -> Updates` | Geplante ruhige Projektion von Version, Build, Kanal, letzter Prüfung und manueller Primäraktion | Desktop UI |

Feed-URL, öffentlicher EdDSA-Schlüssel und Release-Metadaten sind technische
Buildkonfiguration, keine fachlichen Datenquellen. Private EdDSA- und
Developer-ID-Schlüssel, Notarisierungszugänge, Passwörter und Feed-Publishing-
Credentials sind ausdrücklich keine Repository-, Bundle-, Log- oder
Supportpaketnamen.

## Sprint 0.2B.6 - Produktives macOS-Supportwerkzeug

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `PRODUCT_SUPPORT_KEY_REGISTRY` | Versioniertes, reviewbares Manifest ausschließlich öffentlicher Produktivschlüssel; ab `0.2.2` mit `support-2026-b` aktiv | Security Infrastructure |
| `SUPPORT_KEY_REGISTRY_FORMAT_VERSION` | Strikte Manifestversion der Public-Key-Registry, initial `1` | Security Infrastructure |
| `Jenaplan-Support-Reset.command` | Finder-Starter ohne Secretargumente für den geführten Offline-Signaturprozess | Support-Betrieb |
| `support_reset_cli` | Deutsche interaktive Supportprojektion für Anfrageprüfung, Schlüsselpaarprüfung, Laufzeit und sicheren Tokenexport | Support-Betrieb |
| `Jenaplan-Support-Schluessel-einrichten.command` | Getrennter Finder-Starter für die bewusste externe Ed25519-Provisionierung | Support-Betrieb |
| `keypair_cli` | Deutsche interaktive Provisionierung ausschließlich verschlüsselter PKCS#8-Schlüssel außerhalb von Repository und Builds | Support-Betrieb |
| `Jenaplan-Kompetenzmanager-0.2.2-Support-Reset-macOS.zip` | Eigenständiges arm64-Supportpaket ohne App, Fachdaten, Secrets oder Testschlüssel | Packaging |
| `scripts/build_macos_support_reset_package.sh` | Separater reproduzierbarer Build der beiden Support-Executables und des Support-ZIPs | Packaging |
| `scripts/build_support_reset_package.py` | Allowlists, Prüfsummen, deterministisches ZIP und Secret-/Pfadscan für das Supportpaket | Packaging |

Registry-Schlüsselzustände sind `active`, `retiring`, `retired` und `revoked`.
Nur `active` und das kurze Rotationsfenster `retiring` sind verifizierbar;
`retired` und `revoked` sind fail-closed. Private Schlüssel, Passphrasen,
Anfragen und Tokens sind keine Registry- oder Buildnamen.

Registry-Format 1 verlangt technisch `not_after`. Für `support-2026-b` bildet
`9999-12-31T23:59:59Z` ausdrücklich „kein bewusst terminiertes Ablaufdatum“ ab;
das ist keine Aufhebung von Rotation oder sofortigem Widerruf per App-Release.

## Version 0.2.0 - UI-Stabilitätsnachschnitt

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `ensure_button_text_width` | Bestimmt eine sichere Button-Mindestbreite aus finaler Schriftmetrik, Innenabstand und Fokusreserve | Desktop UI |
| `stabilize_message_box_buttons` | Wendet vollständige Textbreiten und ruhigen Abstand auf vorhandene `QMessageBox`-Aktionen an | Desktop UI |
| `workspace_screen` | Wählt bevorzugt den Bildschirm des besitzenden Hauptfensters und sonst den aktuellen beziehungsweise primären Qt-Bildschirm | Desktop Window Policy |
| `prepare_maximized_workspace` | Begrenzt Mindestgröße und Geometrie eines Arbeitsdialogs auf die verfügbare Bildschirmfläche ohne Vollbild-Space | Desktop Window Policy |
| `exec_maximized_workspace` | Öffnet einen vorbereiteten Arbeitsdialog maximiert und modal über den bestehenden Qt-Dialogvertrag | Desktop Window Policy |

Diese Namen steuern ausschließlich Qt-Layout und Fensterzustand. Sie besitzen
keine fachliche Datenquelle, keine Persistenz und keine Plattformauthentifizierung.

## Sprint 0.2R - Release-Artefakte

| Name | Bedeutung | Eigentümer |
|---|---|---|
| `release` | leerer macOS-Buildmodus ohne Pilot-, Fach- oder Runtime-Daten | Packaging |
| `--with-laura-package` | expliziter Zusatzschalter für beide getrennten Pilot-Übergabepakete; ohne Schalter baut `release` kein ZIP | Packaging |
| `Jenaplan-Kompetenzmanager-0.2.0-macOS-arm64.dmg` | kanonisches Installationsartefakt des Pilot-Release-Kandidaten | Packaging |
| `RELEASE_INVENTORY-0.2.0.txt` | Build-Inventar mit Version, Commit, Plattform, Signaturstatus, Hashes und offenen realen Prüfungen | Release-Build |
| `SHA256SUMS-0.2.0.txt` | SHA-256-Liste der freigegebenen Release-Ausgaben | Release-Build |
| `Jenaplan-Kompetenzmanager-0.2.0-Pilotpaket-Leer-macOS-arm64.zip` | Erststart-Übergabepaket aus leerem DMG, Dokumenten, kanonischer Testmappe, Hinweisen und Prüfsummen | Release-Build |
| `Jenaplan-Kompetenzmanager-0.2.0-Pilotpaket-Laura-Testdaten-macOS-arm64.zip` | fachliches Pilot-Übergabepaket mit demselben leeren DMG und separatem synthetischem Restore-Artefakt | Release-Build |
| `Laura-Testdaten-0.2.0.jkmbackup` | verifiziertes offizielles Backupformat mit ausschließlich synthetischem Acht-Monats-Fachdatenbestand; kein Security- oder Kontozustand | Release-Build |
| `scripts/build_laura_testdata_backup.py` | erzeugt den isolierten Seed, erstellt das SQLite-sichere Backup und prüft seine Zählwerte und Security-Ausschlüsse | Packaging |

Diese Namen bezeichnen Build-Artefakte und keine neuen fachlichen Entitäten,
Datenquellen oder Runtime-Verträge.

## Sprint 0.2B.5 - Sichtbarer Support-Reset-Handoff

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `SupportResetVerificationResult` | Datensparsame erfolgreiche Tokenprüfung ohne Konsum oder Reset | Security Domain |
| `SupportResetService.verify_token` | Vollständige bindende Tokenprüfung ohne Backup/Mutation | Security Application |
| `SupportResetDialog` | Modaler mehrstufiger Auth-/Settings-Ablauf ohne Signatur- oder SQLite-Logik | Desktop UI |
| `SupportResetBackupFactory` | Erzeugt den bestehenden verifizierten Backup-Port aus RuntimePaths | Desktop Adapter |
| `SupportResetOperationWorker` | Nicht abbrechbarer Qt-Worker für Prüfung beziehungsweise Backup+Reset | Desktop Controller |
| `.jkmresetrequest` | Versionierter kanonischer technischer Anfrageexport | Support-Betrieb |
| `.jkmresettoken` | Optionaler lokaler Token-Dateiaustausch; niemals persistenter App-State | Support-Betrieb |
| `support_reset_request_created` | Datenschutzneutrales Security-Ereignis | Security Logging |
| `support_reset_token_rejected` | Datenschutzneutrales Security-Ereignis | Security Logging |
| `support_reset_token_accepted` | Datenschutzneutrales Security-Ereignis | Security Logging |
| `support_reset_backup_started` | Datenschutzneutrales Security-Ereignis | Security Logging |
| `support_reset_backup_failed` | Datenschutzneutrales Security-Ereignis | Security Logging |
| `support_reset_completed` | Datenschutzneutrales Security-Ereignis | Security Logging |

`DEFAULT_SUPPORT_KEY_REGISTRY` enthält ab `0.2.2` ausschließlich den vom
Product Owner bestätigten öffentlichen Schlüssel `support-2026-b`. Testkeys und
private Schlüssel sind keine Produktnamen oder Bundle-Ressourcen.

## Sprint 0.2B.4a - Gerätecredential und lokale Authentifizierung

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `DeviceCredential` | Persistenter, widerrufbarer Verifikationsdatensatz ohne Secret | Security Domain |
| `DeviceCredentialStatus` | `pending`, `active` oder `revoked` | Security Domain |
| `DeviceCredentialRepository` | Port für Credential-Metadaten im Security Store | Security Application |
| `DeviceSecretStore` | Port für Klartext-Gerätegeheimnisse im Plattform-Secret-Store | Security Application |
| `LocalDeviceAuthenticator` | Port für lokale OS-Authentifizierung ohne biometrische Rohdaten | Security Application |
| `DeviceCredentialService` | Registrierung, Verifikation, Rotation und Widerruf | Security Application |
| `DeviceCredentialAuthenticationStatus` | `authenticated`, `not_configured`, `rejected`, `unsupported`, `store_unavailable` | Security Domain |
| `LocalAuthenticationAvailability` | `available`, `not_available`, `not_enrolled`, `locked_out`, `unsupported`, `error` | Security Domain |
| `LocalAuthenticationResult` | `success`, `user_cancel`, `fallback_requested`, `not_available`, `not_enrolled`, `locked_out`, `system_cancel`, `failed`, `error` | Security Domain |
| `MacOSKeychainSecretStore` | Security.framework-Adapter für nicht synchronisierendes Gerätegeheimnis | Infrastructure macOS |
| `MacOSLocalDeviceAuthenticator` | LocalAuthentication.framework-Adapter | Infrastructure macOS |
| `UnsupportedDeviceSecretStore` | Sicherer Nicht-macOS-Adapter ohne Dummy-Secret | Infrastructure |
| `UnsupportedLocalDeviceAuthenticator` | Sicherer Nicht-macOS-Adapter mit `unsupported` | Infrastructure |
| `device_credentials` | Security-v3-Tabelle mit Hash-/Bindungs-/Statusmetadaten | Security Store |
| `credential_id` | Zufällige UUIDv4 eines Credentials; nie vollständig geloggt | Security Domain |
| `hash_format_version` | Version des Credential-Verifikationsformats, initial `1` | Security Domain |
| `security_epoch_at_issue` | Epoch-Bindung zum Ausstellungszeitpunkt | Security Domain |
| `device_label` | Technisches datensparsames Label ohne Seriennummer/Fingerprint | Security Domain |
| `device_credential_enabled` | Datenminimiertes technisches Ereignis | Security Logging |
| `device_credential_disabled` | Datenminimiertes technisches Ereignis | Security Logging |
| `device_credential_rejected` | Datenminimiertes technisches Ereignis | Security Logging |
| `local_auth_success` | Datenminimiertes technisches Ereignis | Security Logging |
| `local_auth_cancelled` | Datenminimiertes technisches Ereignis | Security Logging |
| `local_auth_unavailable` | Datenminimiertes technisches Ereignis | Security Logging |

Dieses Dokument ist ab Sprint 4 die verbindliche Registry fuer technische Namen.

## Sprint 0.2B.4 - Produktive Security-Startintegration

Registrierte Module: `src.core.app_preferences`, `src.core.onboarding`,
`src.security.startup`, `src.security.session`, `src.desktop_app.security_ui`,
`src.desktop_app.security_controller` und
`src.desktop_app.screens.onboarding_screen`.

Startzustaende: `SecurityStartState` mit `first_run`, `legacy_enrollment`,
`login_required`, `recovery_available`, `password_reset_pending`, `locked`,
`authenticated`, `inconsistent`, `corrupt`, `unsupported_version` und
`fatal_security_error`. `SecurityStartupResolver` erzeugt genau einen Zustand;
boolesche Mehrfachdeutungen und stille Reparaturen sind ausgeschlossen.

Runtime-/Application-Namen: `prepare_security_runtime_storage`,
`SecurityRuntimePaths`, `AppPreferences`, `AppPreferencesFile`,
`AppPreferencesError`, `normalize_display_name`, `DISPLAY_NAME_MAX_LENGTH`,
`OnboardingStatus`, `ONBOARDING_FORMAT_VERSION`, `ONBOARDING_STEP_COUNT`,
`OnboardingController`, `OnboardingSession`, `InMemorySession`,
`SecuritySessionController`, `SessionLockReason`, `SessionActivityKind` und
`WakeObservation`. `app-preferences.json` liegt in
der Runtime-Wurzel, enthaelt ausschliesslich das erlaubte
Inaktivitaetsintervall, den optionalen normalisierten `display_name`,
`onboarding_status`, `onboarding_current_step`,
`onboarding_format_version` und die boolesche Bedienpräferenz
`touch_id_preferred` und ist weder Security-Store noch fachliche
Datenquelle. Zulaessige Onboarding-Zustaende sind `not_started`,
`in_progress`, `completed` und `dismissed`. `dashboard_greeting` ist die reine
lokale Zeitprojektion fuer Morgen, Tag und Abend.

Qt-Namen: `AuthenticationDialog`, `SecurityOperationWorker`,
`RecoveryCodesPage`, `SecurityUiCoordinator`, `ApplicationActivityFilter` und
`WakeMonitor`, `OnboardingScreen`, `OnboardingStatusProjection`,
`OnboardingStatusItem`, `OnboardingStep` und `OnboardingAction`. Das technische
Shell-Signal `restore_handoff_started` beendet
eine bereits bestaetigte Restore-Uebergabe auch hinter der Sperransicht. Qt
zeigt an, sammelt Eingaben und leitet Signale weiter; Hashing,
Policy, Drosselung, Epoch und Zustandsuebergaenge bleiben im Security Core.

Security-Ereigniscodes: `login_success`, `login_failed`, `lock_manual`,
`lock_inactivity`, `lock_wake`, `recovery_started`, `recovery_completed` und
`password_changed`. Logs enthalten keine Passwoerter, Codes, Hashes,
vollstaendigen IDs oder fachlichen Inhalte.

## Sprint 0.2B.3 - Signierter Support-Reset-Core

Registrierte Module und Werkzeuge:

- `src.security.support_reset`
- `src.security.infrastructure.ed25519`
- `src.security.infrastructure.key_registry`
- `src.application.commands.security_backup`
- `tools/generate_support_keypair.py`
- `tools/generate_support_reset.py`
- `tests/test_support_reset.py`
- `tests/test_support_reset_tools.py`

Versionen und Formate:

- `SECURITY_SCHEMA_VERSION = 2`; `SECURITY_FORMAT_VERSION = 1` bleibt unveraendert.
- `SUPPORT_RESET_FORMAT_VERSION = 1`, Envelope `JKM-SR1`.
- `SUPPORT_RESET_ALGORITHM = "Ed25519"`.
- `SUPPORT_RESET_ACTION = "reset_local_password_v1"`.
- `reset_request_id`: zufaellige UUIDv4 ohne Personenbezug.
- `nonce`: 32 kryptografisch zufaellige Bytes in striktem Base64url ohne Padding.
- `key_id`: registrierte technische Identitaet eines oeffentlichen Schluessels.
- `token_digest`: SHA-256 ueber die vollstaendigen UTF-8-Tokenbytes; vollstaendige Tokens werden nicht persistiert.
- `security_epoch`: persistente monotone Generation pro Konto und Installation.

Domain/Application-Namen: `SupportResetRequest`, `SupportResetPayload`,
`SupportResetFailureCode`, `SupportResetRejected`, `SupportResetResult`,
`SupportResetService`, `SupportResetTokenCodec`, `SupportSecurityBackupPort`,
`SupportResetSignatureVerifier` und die erweiterten `SecurityRepository`-Ports.

Infrastructure-Namen: `Ed25519SignatureVerifier`, `SupportPublicKey`,
`SupportPublicKeyStatus`, `PublicKeyRegistry` und `DEFAULT_SUPPORT_KEY_REGISTRY`. Die
Default-Registry enthaelt ohne freigegebenen Produktivschluessel keinen
nutzbaren Schluessel. Testschluessel liegen ausschliesslich unter `tests/` und
werden nicht paketiert.

Tabellen: `support_reset_requests`, `support_reset_token_uses` und
`security_epochs`. Zustaende fuer Anfragen sind `active`, `revoked` und
`consumed`; Schluesselzustaende sind `active`, `retiring` und `revoked`.

Es entstehen keine View, kein UI-Feld, keine Qt-Integration, kein normaler
Autostart und keine Sitzung.

## Sprint 0.2B.2 - Security Core

Registrierte Module:

- `src.security.domain`
- `src.security.ports`
- `src.security.application`
- `src.security.infrastructure.argon2_hasher`
- `src.security.infrastructure.sqlite_repository`
- `src.security.infrastructure.system`
- `tests/test_security_core.py`
- `tests/test_security_recovery.py`

Runtime-Namen und Versionen:

- `RuntimePaths.security`: kanonisches Security-Verzeichnis unter der Runtime-Wurzel.
- `RuntimePaths.security_database`: `<runtime-root>/security/security.sqlite`.
- `RuntimePaths.enrollment_marker`: `<runtime-root>/security/enrollment.marker`.
- Security-Schema v1 war der Ausgangsstand; Sprint 0.2B.3 migriert kontrolliert auf v2. `SECURITY_FORMAT_VERSION = 1` und `ENROLLMENT_MARKER_VERSION = 1` bleiben unveraendert.
- `PASSWORD_HASH_FORMAT_VERSION = 1` fuer Argon2id-PHC-Strings.
- `RECOVERY_CODE_FORMAT_VERSION = 1` fuer `JKM1-XXXX-XXXX-XXXX-XXXX-C`.
- `installation_id`: zufaellige UUIDv4; Supportdarstellung `INS-<uuid>`.
- `user_id`, `recovery_set_id` und `recovery_code_id`: zufaellige UUIDv4 ohne Personenbezug.

Domain- und Application-Namen:

- `SecurityStoreState`: `uninitialized`, `ready`, `password_reset_pending`, `inconsistent`, `corrupt` oder `unsupported_version`.
- `AccountStatus`: `active`, `password_reset_pending` oder `disabled`.
- `AuthenticationStatus`: `authenticated`, `invalid_credentials`, `throttled`, `store_unavailable` oder `password_reset_required`.
- `PasswordPolicy`, `PasswordPolicyError` und strukturierte `PasswordViolation`-Codes.
- `SecurityApplicationService`, `EnrollmentResult`, `AuthenticationResult`, `LockState`, `RecoveryPreparation` und `RecoveryConsumptionResult`.
- Ports `SecurityRepository`, `PasswordHasher`, `RandomSource`, `UtcClock`, `MonotonicClock`, `EnrollmentMarkerStore` und `FilePermissionManager`.

Infrastructure-Namen:

- `SQLiteSecurityRepository`: kurzlebige Verbindungen, `foreign_keys=ON`, kontrolliertes WAL und `BEGIN IMMEDIATE` fuer kritische Schreibvorgaenge.
- `Argon2idPasswordHasher`: Memory 65536 KiB, Time 6, Parallelism 1, Salt 16 Byte, Hash 32 Byte, PHC-String.
- `SystemRandomSource`, `SystemClock`, `EnrollmentMarkerFile` und `PlatformFilePermissionManager`.

Die Security-Namen sind keine fachlichen IDs. Sie besitzen keine Verbindung zu
Autorennamen oder fachlichen Tabellen. Es gibt keine Security-View, kein
Security-UI-Feld und keine Qt-Integration in diesem Sprint.

## Sprint 0.2A.4a - Asynchrone Settings-Operationen

- Modul `src.desktop_app.backup_restore_operations`
- `BackupRestoreOperationsController`: shell-eigener Qt-Controller fuer genau eine technische Operation gleichzeitig.
- `BackupRestoreOperationWorker`: widgetfreier `QObject`-Worker, der genau einen vorhandenen Application-Service-Aufruf in einem `QThread` ausfuehrt.
- `BackupRestoreOperation`: unveraenderlicher, nach Operationstyp und vorhandenem Application-Command typgepruefter Auftrag.
- `BackupRestoreOperationType`: `create_backup`, `discover_verified_backups`, `verify_backup`, `verify_restore_backup`, `prepare_restore_staging`, `verify_prepared_restore`, `create_restore_safety_backup`.
- `BackupRestoreProgressPhase`: neutrale technische Phase ohne Prozentwert und ohne Core-Fehlertext.
- `BackupRestoreOperationsState`: ausschliesslich `idle`, `running`, `finishing`.
- `BackupRestoreOperationErrorInfo`: datensparsame Fehlerprojektion aus Operationstyp und Fehlerklasse ohne Exception-Text, Pfad oder fachlichen Inhalt.

Regel: Der Worker greift nie auf Widgets, Dialoge, `QApplication`, Lock-Handoff oder App-Beendigung zu. Er dupliziert keine Backup-/Restore-Logik und wird nie mit `terminate()` beendet.

## Sprint 0.2A.4 - Einstellungsnavigation und Backup-/Restore-UI

- `BackupRestoreDesktopAdapter`: Desktop-Adapter fuer Runtime-gebundene Backup-/Restore-Commands ohne Qt-Screen- oder Fachlogik.
- `BackupSummaryViewModel`: datensparsame Anzeige einer vollstaendig verifizierten Sicherung.
- `RestorePreviewViewModel`: datensparsame Anzeige der vorhandenen technischen Restore-Vorschau.
- `SettingsNavigationCard`: tastaturbedienbare Einstellungszeile fuer einen lokalen Bereich.

Regel: Diese Namen beschreiben nur allgemeine Betriebs- und UI-Projektionen. Sie fuehren keine SQLite-Tabelle, fachliche Entitaet, automatische Sicherung, Aufbewahrung oder neue fachliche Datenquelle ein.

## Sprint 0.2A.3c - Produktiver Worker-Restore

Registrierte Python-Module:

- `src/core/restore_runtime.py`
- `src/desktop_app/restore_worker.py`
- `src/application/commands/restore.py`
- `tests/test_restore_runtime.py`

Technische Runtime-Namen:

- `instance.lock`: exklusiver, an die kanonische Runtime-Wurzel gebundener Instanz-/Restore-Lock mit ausschliesslich PID, Prozessstart-Identitaet und UTC-Zeit.
- `restore-handoffs/<restore-id>.json`: noch nicht konsumierte einmalige Handoff-Datei, Modus `0600`.
- `restore-handoffs/<restore-id>.consumed.json`: atomar konsumierte Handoff-Datei; ihre Existenz blockiert Wiederverwendung.
- `restore-transactions/<restore-id>/`: ausschliesslich aus Runtime-Wurzel und Restore-ID abgeleiteter Transaktionsbereich.
- `source-backup.jkmbackup`: in den Transaktionsbereich stabil kopierte und an Groesse/SHA-256 gebundene Restore-Quelle; der Worker erhaelt keinen frei interpretierbaren Archivpfad.
- `current-state.json`: atomar ersetzter kanonischer aktueller Restore-Zustand.
- `events.jsonl`: append-only technisches Ereignisjournal.
- `rollback/`: alter Live-Bestand aus DB, WAL, SHM und `documents/`.
- `failed-new/`: nach Fehler aus Live zurueckgenommener neuer Bestand.
- `resume-token.json`: einmaliger kurzlebiger Startup-Handshake-Token, Modus `0600`.
- `resume-token.consumed.json`: atomar konsumierter Resume-Token.

Technische Versionen und IDs:

- `RESTORE_HANDOFF_VERSION = 1`
- `RESTORE_JOURNAL_VERSION = 1`
- `RESTORE_RESUME_TOKEN_VERSION = 1`
- `restore_id`: bestehende technische Restore-ID nach `_RESTORE_ID_PATTERN`.
- `nonce`: kryptografisch zufaelliger URL-sicherer Wert ohne fachliche Bedeutung.
- `staging_state_sha256`: SHA-256 der kanonischen `staging-state.json`-Bytes.
- `prepared_database_sha256`: SHA-256 der vollstaendig geprueften Prepared-V1-Datenbank.

Zustaende: `handoff_created`, `worker_started`, `maintenance`,
`preflight_verified`, `replacement_started`, `installed_verified`,
`completed`, `rolled_back`, `aborted_before_replacement` und
`manual_recovery_required`.

Application-Namen: `CreateRestoreHandoffCommand`, `ExecutePreparedRestoreCommand`, `RecoverInterruptedRestoreCommand` und `ConfirmRestoreStartupCommand`.

Worker-Start: Entwicklerbetrieb ueber
`python3 -m src.desktop_app.restore_worker --handoff <datei>`; Paketbetrieb
ueber fruehen `--restore-worker`-Dispatch im gebuendelten Executable vor Qt-
und Runtime-Initialisierung. `RestoreWorkerLaunchPlan` bindet Executable,
Argumentliste und Arbeitsverzeichnis ohne Shellauswertung.
`RestoreWorkerProcess` haelt den bestaetigten separaten Prozess und den nur bis
zum Ende der Haupt-App offenen Parent-Lebensdauerkanal. Die technischen
Argumente `--ready-fd` und `--parent-lifetime-fd` transportieren keine
fachlichen Daten oder Secrets: Der erste Kanal bestaetigt exakt
`worker_started`, der zweite wird erst durch das vollstaendige Prozessende der
Haupt-App geschlossen.
`Packaged Restore Worker Smoke` bezeichnet den Build-Gate-Test
`scripts/smoke_test_packaged_restore_worker.py`, der den echten Executable aus
dem signierten `.app`-Bundle als separaten Restore-Worker startet, die
persistente Uebernahme ohne Live-Aenderung prueft und den Testprozess
anschliessend kontrolliert beendet und reappt.

## Sprint 0.2A.3b - Restore-Staging, V0-V1-Migration und Sicherheitsbackup

Registrierte Python-Module:

- `src/core/restore.py`
- `src/application/commands/restore.py`
- `tests/test_restore.py`

Registrierte Konstanten und technische Pfade:

- `RESTORE_STAGING_DIRECTORY = "restore-staging"`
- `RESTORE_SOURCE_DIRECTORY = "source"`
- `RESTORE_PREPARED_DIRECTORY = "prepared"`
- `RESTORE_STATE_FILENAME = "staging-state.json"`
- `RESTORE_SAFETY_DIRECTORY = "restore-safety"`
- `restore-staging/<restore-id>/source/`
- `restore-staging/<restore-id>/prepared/`
- `backups/restore-safety/<restore-id>/`

Registrierte unveraenderliche Datenobjekte:

- `RestoreStagingPaths`
- `RestoreStagingResult`
- `PreparedRestoreVerificationResult`
- `RestoreSafetyBackupResult`

Registrierte Fehlerklassen:

- `RestoreStagingError`
- `RestoreStateError`
- `RestoreMigrationError`
- `RestoreMaterializationError`
- `RestoreSafetyBackupError`

Registrierte Services und Application-Vertraege:

- `RestoreStagingService`
- `RestoreSafetyBackupService`
- `RuntimeRestorePathSet`
- `BackupVerifier.parse_manifest(manifest_bytes)`
- `RestoreVerifier.verify_extracted(extraction_root, manifest)`
- `PrepareRestoreStagingCommand`
- `CreateRestoreSafetyBackupCommand`
- `VerifyPreparedRestoreQuery`
- `CleanupRestoreStagingCommand`
- `RestoreApplicationService.prepare_staging(command)`
- `RestoreApplicationService.create_safety_backup(command)`
- `RestoreApplicationService.verify_prepared(query)`
- `RestoreApplicationService.cleanup_staging(command)`

Registrierte technische Phasen:

- `source_extracted`
- `database_prepared`
- `files_materialized`
- `paths_rebased`
- `completed`
- `failed`

Regel: Diese Namen gehoeren ausschliesslich zur allgemeinen Betriebsfunktion. Restore-IDs sind technische Identitaeten und duerfen keine fachlichen Werte enthalten. Staging-State, Preview und Ergebnisse enthalten keine Namen, fachlichen Texte, Originaldateinamen oder fachlichen Pfade. Es entstehen keine neue SQLite-Tabelle, fachliche Entitaet, sichtbare View, UI-Aktion, Live-Migration oder Restore-Ausfuehrung.

## macOS Pilot-Deployment

| Technischer Name | Bedeutung |
| --- | --- |
| `APP_VERSION` | einzige Projektquelle fuer die technische Pilot-Paketversion |
| `de.jenaplan.kompetenzmanager` | stabile macOS-Bundle-ID |
| `JENAPLAN_APP_DATA_DIR` | ausschliesslich technischer Override des Benutzerpfads fuer automatisierte Pakettests |
| `RuntimePaths` | Pfadprojektion fuer Datenbank, Dokumente, Exporte, Backups und Logs |
| `pilot_build_info.json` | nicht geheime Buildmetadaten mit Version, Architektur, Git-HEAD, Quellbaumzustand und Pilotdatenvariante |
| `pilot_initial` | optionaler, unveraenderlicher Bundlebereich fuer explizite fiktive Laura-Startdaten |
| `empty` | technische Smoke-Test-Variante ohne gepackte SQLite-Datei oder Schuelerdaten |
| `laura` | Lehrkraft-Pilotvariante mit ausschliesslich fiktiven Daten aus `scripts/seed_test_data.py` |
| `FIKTIVE_PILOTDATEN.txt` | sichtbare technische Kennzeichnung der fiktiven Startdaten im Laura-Payload |
| `scripts/build_laura_pilot_package.py` | reproduzierbare Zusammenstellung der getrennten leeren und Laura-Testdaten-Übergabeordner und ZIPs aus aktuellen Release-Ausgaben |
| `00_START_HIER.txt` | versionierter Einstiegstext im Laura-Uebergabepaket |
| `PILOT_VERSION.txt` | versionierte Inhalts- und Datenkennzeichnung im Laura-Uebergabepaket |

## Sprint 0.2A.2 - Backup-Backend und Integritaetspruefung

Registrierte Python-Module:

- `src/core/backup.py`
- `src/application/commands/backup.py`
- `tests/test_backup.py`

Registrierte Fehlerklassen:

- `BackupError`
- `BackupValidationError`
- `BackupIntegrityError`
- `BackupBusyError`
- `BackupFileError`
- `BackupFormatError`

Registrierte unveraenderliche Datenobjekte:

- `BackupManifest`
- `BackupDatabaseInfo`
- `BackupManagedFile`
- `BackupExternalReferenceSummary`
- `BackupCounts`
- `BackupResult`
- `BackupVerificationResult`
- `RuntimePathSet`

Registrierte Services und Application-Vertraege:

- `SQLiteBackupEngine`
- `BackupInventoryService`
- `BackupService`
- `BackupVerifier`
- `CreateBackupCommand`
- `VerifyBackupQuery`
- `BackupApplicationService`
- `SQLiteBackupEngine.schema_fingerprint(database_path)`

Registrierte technische Werte und Pfade:

- `.jkmbackup`
- `jenaplan-kompetenzmanager-backup`
- `backup_format_version` mit Wert `1`
- `compatibility_version` mit Wert `1`
- `manifest.json`
- `database/kompetenzmanager.sqlite`
- `files/<technical-id>.<neutral-extension>`
- `Jenaplan-Kompetenzmanager-Backup-YYYYMMDDTHHMMSSZ.jkmbackup`
- Command-Name `backup.create`
- Umgebungsmarker `JENAPLAN_PACKAGED_SMOKE_MARKER` mit dem festen technischen Wert `isolated-v1`

Validierte technische Buildwerte im Manifest:

- `app_version`: kanonische SemVer-aehnliche Produktversion oder `unknown`
- `build_commit`: Git-Hex-ID mit 7 bis 64 Zeichen oder `unknown`
- `source_tree_state`: ausschliesslich `clean` oder `dirty`, falls vorhanden

Regel: Diese Namen gehoeren ausschliesslich zur allgemeinen Betriebsfunktion. Der Smoke-Marker ist nur gemeinsam mit einer geprueften temporaeren Datenwurzel gueltig und ersetzt den Pfadnachweis nicht. Die Namen fuehren keine SQLite-Tabelle, Migration, fachliche Entitaet, sichtbare View, UI-Aktion, Restore-Freigabe oder Universal-Storage-Engine ein.

## Sprint 0.2A.3a - Datenbank-Kompatibilitaet und Restore-Verifier

Registrierte Python-Module:

- `src/core/database_compatibility.py`
- `src/core/restore.py`
- `src/application/commands/restore.py`
- `tests/test_database_compatibility.py`
- `tests/test_restore.py`

Registrierte Konstanten und technische Werte:

- `BACKUP_FORMAT_VERSION = 1`
- `DATABASE_COMPATIBILITY_VERSION = 1`
- `V1_COMPATIBILITY_FINGERPRINT`
- `KNOWN_UNVERSIONED_V1_PREDECESSOR_FINGERPRINT`
- SQLite `PRAGMA user_version`
- `DatabaseCompatibilityStatus.EXACT`
- `DatabaseCompatibilityStatus.MIGRATION_REQUIRED`
- `DatabaseCompatibilityStatus.INCOMPATIBLE`

Registrierte unveraenderliche Datenobjekte:

- `DatabaseSchemaIdentity`
- `DatabaseVersionInfo`
- `DatabaseCompatibilityResult`
- `RestoreCompatibility`
- `RestorePreview`
- `RestoreVerificationResult`
- `VerifyRestoreBackupQuery`

Registrierte Fehlerklassen:

- `DatabaseCompatibilityError`
- `UnsupportedDatabaseVersionError`
- `UnknownDatabaseSchemaError`
- `DatabaseVersionMismatchError`
- `RestoreError`
- `RestoreFormatError`
- `RestoreCompatibilityError`
- `RestoreIntegrityError`

Registrierte Services:

- `DatabaseCompatibilityInspector`
- `DatabaseCompatibilityPolicy`
- `RestoreVerifier`
- `RestoreApplicationService`
- `BackupVerifier.extract_isolated(archive, extraction_root)`

Regel: Diese Namen beschreiben ausschliesslich read-only ermittelbare Datenbank-Kompatibilitaet und technische Restore-Verifikation. Sie fuehren keine fachliche Entitaet, neue SQLite-Tabelle, Migration, persistentes Staging, Live-Austausch, Desktop-Adapter, sichtbare View oder UI-Aktion ein. `APP_VERSION` bleibt unabhaengig von Backupformat- und Datenbank-Kompatibilitaetsversion.

## Grundregeln

Technische Namen werden grundsaetzlich englisch und ASCII-kompatibel gefuehrt.

Technische Namen enthalten keine Umlaute, keine Leerzeichen und keine sichtbaren deutschen UI-Begriffe.

Sichtbare Blattnamen und UI-Texte duerfen deutsch sein. Technische Schluessel bleiben stabil und englisch oder bereits registrierte ASCII-Namen.

Sichtbare Begriffe duerfen sich aendern. Technische Namen bleiben stabil.

Keine neuen technischen Namen ohne Erweiterung dieser Registry.

Bestehende technische Namen werden nicht ohne eigenen Migrationssprint umbenannt.

Beispiele fuer stabile technische IDs:

- `student_id`
- `group_id`
- `course_id`
- `subject_id`
- `competency_id`
- `observation_id`
- `media_id`

Beispiele fuer technische Feldnamen:

- `file_ref`
- `media_category`
- `updated_at`

Beispiele fuer sichtbare Begriffe:

- Stammgruppe
- Kurs
- Schuelerprofil
- Kompetenz
- Lernentwicklungsbericht

## Workbook-CodeNames

Status: Archivierter Legacy-Pfad unter `legacy/excel/`. Bestehende Workbook-CodeNames bleiben fuer historische Arbeitsmappen und reproduzierbare Altstaende stabil. Neue Hauptanwendungsfeatures erzeugen keine neuen Workbook-CodeNames.

| Objekt | Sichtbar | Technisch | Status |
| --- | --- | --- | --- |
| Workbook | Arbeitsmappe | `DieseArbeitsmappe` | bestehend |
| Stammgruppenuebersicht | `Stammgruppenübersicht` | `wsClassOverview` | bestehend, nicht umbenennen |
| Schuelerprofil | `Schülerprofil` | `wsStudentProfile` | bestehend |
| Neuer-Schueler-Dialogseite | `dlg_neuer_schueler` | `wsDialogNewStudent` | Feature 1, worksheet-basierter Dialog |

Hinweis: `wsClassOverview` bleibt trotz sichtbarer Umbenennung auf `Stammgruppenübersicht` bestehen. Eine technische Umbenennung ist kein Bestandteil von Sprint 4.0.

## Legacy-Regeln

Bestehende technische Namen wie `wsClassOverview`, `ui_class_search`, `ui_class_search_input` und `ui_action_new_observation` werden vorerst nicht umbenannt.

Sie gelten als technische Altlasten und bleiben stabil, bis eine kontrollierte Migration in dieser Registry dokumentiert und freigegeben ist.

Keine spontane Umbenennung bestehender technischer Namen waehrend Feature-Sprints.

## Sichtbare Blattnamen

| Sichtbarer Blattname | Zweck |
| --- | --- |
| `Stammgruppenübersicht` | Einstieg in eine Stammgruppe |
| `Schülerprofil` | Profil eines Schuelers |
| `dlg_neuer_schueler` | worksheet-basierte Dialogseite fuer neuen Schueler |
| `Kursübersicht` | zukuenftige Ansicht fuer einen Kurs |

## Hidden-Data-Sheets

Status: Legacy-Workbook-Projektion unter `legacy/excel/`. Aktive PySide-Features nutzen SQLite, Adapter und ViewModels statt Hidden Sheets.

Workbook-Datenquellen verwenden das Praefix `data_`.

Registrierte Hidden-Data-Sheets:

- `data_students`
- `data_groups`
- `data_courses`
- `data_subjects`
- `data_competencies`
- `data_observations`
- `data_observation_competencies`
- `data_media`
- `data_settings`

## Tabellen

Status: Legacy-Workbook-Projektion unter `legacy/excel/`. Aktive PySide-Features nutzen SQLite-Tabellen und ViewModels.

Tabellennamen verwenden das Praefix `tbl_` und beziehen sich auf das jeweilige Hidden-Data-Sheet.

Registrierte Tabellennamen:

- `tbl_students`
- `tbl_groups`
- `tbl_courses`
- `tbl_subjects`
- `tbl_competencies`
- `tbl_observations`
- `tbl_observation_competencies`
- `tbl_media`
- `tbl_settings`

## Aktive SQLite-Tabellen

Aktive SQLite-Tabellen verwenden englische, ASCII-kompatible technische Namen.

Registriert:

- `students`
- `groups`
- `courses`
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`
- `competencies`
- `observations`
- `observation_competency_ratings`
- `student_competency_confirmations`
- `documents`
- `documentation_subject_settings`
- `student_documentation_subject_profiles`
- `student_documentation_subject_selections`
- `timetable_entries`
- `report_drafts`
- `report_draft_subjects`
- `report_draft_competencies`
- `report_draft_observations`
- `report_draft_charts`
- `learning_reports`
- `learning_report_revisions`
- `learning_report_pdf_artifacts`
- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`
- `learning_conferences`
- `learning_conference_revisions`
- `learning_conference_pdf_artifacts`

`documentation_subject_settings` speichert ausschliesslich, welche `subject_id` fuer Dokumentations- und Auswertungslogik als dokumentationsrelevant gelten. Die Tabelle ersetzt nicht den Kompetenzkatalog und veraendert `competencies.active` nicht.

`student_documentation_subject_profiles` bindet `inherit` oder `custom`
ausschließlich an `student_id + school_year_id`.
`student_documentation_subject_selections` enthält nur bei `custom` die exakte
normalisierte Fachschlüsselmenge. Beide Tabellen speichern keine Fachnamen,
keine Membershipableitung und keine Beobachtungs- oder Bewertungsdaten.

Die Tabellen mit Praefix `report_draft_` speichern ausschliesslich den bearbeitbaren Arbeitsentwurf eines Lernentwicklungsberichts. Sie sind keine finale Berichtsdomain, enthalten keine Kompetenzbewertung und frieren keine Kompetenz- oder Beobachtungsinhalte ein.

`learning_reports` speichert die stabile Identitaet eines aus genau einem `RPD` hervorgegangenen Lernentwicklungsberichts. `learning_report_revisions` speichert dessen unveraenderliche fachliche Revisionen als kanonischen JSON-Snapshot mit SHA-256-Hash. Beide Tabellen erweitern den Draft additiv; sie veraendern weder `RPD` noch dessen Statusvertrag.

Registrierte technische Felder fuer persistente Berichtsentwuerfe:

- `report_draft_id`
- `learning_report_id`
- `learning_report_revision_id`
- `learning_report_pdf_artifact_id`
- `source_report_draft_id`
- `revision_number`
- `snapshot_schema_version`
- `snapshot_json`
- `snapshot_sha256`
- `relative_file_path`
- `mime_type`
- `file_size_bytes`
- `pdf_sha256`
- `finalized_at`
- `finalized_by_display_name`
- `superseded_at`
- `report_type`
- `period_start`
- `period_end`
- `status`
- `teacher_name`
- `overall_text`
- `strengths_text`
- `development_text`
- `support_needs_text`
- `next_goals_text`
- `chart_type`

Zulaessiger Status in Sprint 7F.1: `draft`.

Zulaessiger Berichtstyp in Sprint 7F.1: `learning_development`.

Zulaessige Diagrammtypen:

- `documentation_coverage`
- `competency_timeline`
- `observation_timeline`

`report_draft_id` verwendet das Format `RPD-######`.

## Sprint-3A-Mapping Kompetenzstruktur

Sprint 3A fuehrt keine neuen technischen Feldnamen und keine neuen SQLite-Spalten ein.

Die sichtbare Fachsprache fuer Kompetenzstruktur lautet:

```text
Fach -> Kompetenzbereich -> Thema -> Kompetenz
```

Mapping auf vorhandene technische Namen:

| Sichtbarer Begriff | Bestehender technischer Name |
| --- | --- |
| Fach | `subject_id` / `subject_name` |
| Kompetenzbereich | `learning_area` |
| Thema | `competency_group` |
| Kompetenz | `description` in `competencies`, `competency_text` in `observation_competency_ratings` |
| Kurzlabel fuer kompakte UI | `label` |

Regel: Keine neuen Feldnamen wie `competency_area` oder `topic` einfuehren, solange dieses Mapping fachlich ausreicht. Sichtbare UI- und Dokumentationsbegriffe duerfen deutsch sein; technische Namen bleiben stabil.

Sprint 3B ergaenzt im CSV-Katalog die optionale Spalte `competency_label`. Sie ist kein neues SQLite-Feld, sondern befuellt beim Katalogimport das bestehende Feld `competencies.label`. Ohne Wert bleibt die bisherige Fallback-Logik auf vorhandene Katalogfelder moeglich.

Bewertungen bleiben technisch in `observation_competency_ratings.rating` gespeichert. `observations` erhaelt keine globale Bewertung. Ein nicht bewerteter oder offener Kompetenzaspekt wird nicht als Ratingwert gespeichert, sondern erzeugt keine Zuordnungszeile in `observation_competency_ratings`.

`is_quick_observation` ist ausschliesslich ein fluechtiger Command-/ViewModel-Name fuer die bewusste Eingabe und Anzeige einer Schnellbeobachtung. Er ist kein SQLite-Feld. Persistiert und rekonstruiert wird der Zustand als aktive Beobachtung mit nichtleerer Notiz und ohne Zeilen in `observation_competency_ratings`.

## Sprint-4A Kompetenzkatalogmodell

Status: Verbindliche technische Namen fuer das produktive Kompetenzkatalogmodell. Sprint 4A speichert diese Felder im CSV-Katalog und in SQLite `competencies`.

Neue CSV-/SQLite-Felder:

| Technischer Name | Zweck |
| --- | --- |
| `learning_stage` | produktbezogene Filterstufe einer Kompetenz, getrennt vom quellenbezogenen `grade_band` |
| `catalog_status` | fachlicher Katalogstatus fuer Freigabe, Bestandsschutz und spaetere Archivierung |
| `activation_group_key` | stabiler, generischer Aktivierungsbereich fuer optionale Kompetenzgruppen |
| `catalog_default_active` | aus dem CSV uebernommene Default-Aktivitaet, getrennt von lokaler SQLite-Aktivitaet `active` |

Zulaessige Werte fuer `learning_stage`:

- `stage_1_3`
- `stage_4`
- `cross_stage`

Zulaessige Werte fuer `catalog_status`:

- `current`
- `legacy`

Optional empfohlene spaetere SQLite-Tabelle:

- `competency_activation_groups`

Regel: `grade_band` bleibt Quellenkontext. `learning_stage` ist die produktbezogene Filterstufe. `active` bleibt lokale SQLite-Aktivierung und wird beim erneuten Katalogimport fuer bestehende `competency_id`s nicht aus dem CSV ueberschrieben. `catalog_default_active` speichert nur den Katalogstandard. `catalog_status = current` ist der Standard; `catalog_status = legacy` ist ausschliesslich fuer historische Kompetenzen vorgesehen. Legacy-Kompetenzen sind standardmaessig keine neuen Dokumentationsziele.

## ID-Felder

Verbindliche ID-Felder fuer neue Architekturarbeit:

- `student_id`
- `group_id`
- `course_id`
- `subject_id`
- `competency_id`
- `observation_id`
- `media_id`
- `report_id`
- `report_draft_id`
- `learning_report_id`
- `learning_report_revision_id`

Bestehende historische Seed-IDs und Prototyp-Bezeichner werden nur kontrolliert migriert.

Die fachlichen Zuordnungsfelder fuer neue Architekturarbeit sind `group_id` und `course_id`.

## ID-Strategie

Die folgende ID-Strategie ist projektweit verbindlich fuer neue fachliche Entitaeten:

| Entity | ID-Feld | Format | Beispiel |
| --- | --- | --- | --- |
| Student | `student_id` | `STU-######` | `STU-000001` |
| Group | `group_id` | `GRP-######` | `GRP-000001` |
| Course | `course_id` | `CRS-######` | `CRS-000001` |
| CourseGroup | `course_group_id` | stabiler technischer Key | `course-group-default` |
| Competency | `competency_id` | `CMP-######` | `CMP-000001` |
| Observation | `observation_id` | `OBS-######` | `OBS-000001` |
| Media | `media_id` | `MED-######` | `MED-000001` |
| ReportDraft | `report_draft_id` | `RPD-######` | `RPD-000001` |
| LearningReport | `learning_report_id` | `RPT-######` | `RPT-000001` |
| LearningReportRevision | `learning_report_revision_id` | `RPV-######` | `RPV-000001` |
| TimetableEntry | `timetable_entry_id` | `TTE-######` | `TTE-000001` |

Regeln:

- IDs sind technische Identitaeten und bleiben stabil.
- Sichtbare Namen duerfen sich aendern, IDs nicht.
- Neue IDs werden fortlaufend je Entity erzeugt.
- Neue `competency_id`s werden global fortlaufend als `CMP-######` erzeugt; es gibt keine fachbezogenen Nummernkreise und keine Wiederverwendung vorhandener oder uebersprungener IDs.
- Historische Seed-IDs wurden fuer Student in Sprint 4.2c kontrolliert migriert.
- VBA-Navigation verwendet weiterhin ausschliesslich das jeweilige ID-Feld, nicht das konkrete Praefix.

## Named Ranges

Status: Archivierter Legacy-Pfad unter `legacy/excel/`. Bestehende Named Ranges bleiben stabil, solange alte Workbook-Projektionen reproduzierbar sein muessen. Neue PySide-Features nutzen keine neuen Named Ranges.

Registrierte bestehende Named Ranges:

- `ui_profile_selected_student_id`
- `ui_profile_back_to_class_overview`
- `ui_student_slot_XX`
- `ui_student_slot_id_XX`
- `ui_class_search`
- `ui_class_search_input`
- `ui_action_new_student`
- `ui_action_new_observation`
- `ui_dialog_new_student_first_name`
- `ui_dialog_new_student_last_name`
- `ui_dialog_new_student_group`
- `ui_dialog_new_student_course`
- `ui_dialog_new_student_notes`
- `ui_dialog_new_student_document_list`
- `ui_dialog_new_student_add_document`
- `ui_dialog_new_student_cancel`
- `ui_dialog_new_student_save`

`XX` steht fuer zweistellige Slotnummern wie `01`, `02`, `03`.

Zukuenftige Named-Range-Muster:

- `ui_competency_slot_XX`
- `ui_competency_slot_id_XX`
- `ui_report_slot_XX`
- `ui_report_slot_id_XX`
- `ui_subject_slot_XX`
- `ui_subject_slot_id_XX`

## Shape-Praefixe

Registrierte bestehende Shape-Praefixe:

- `ui_nav_student_card_`
- `ui_nav_profile_back`

Zukuenftige Shape-Praefixe:

- `ui_nav_competency_card_`
- `ui_nav_report_card_`
- `ui_nav_subject_card_`

Shape-Namen bestehen aus Praefix plus zweistelliger Slotnummer.

Beispiele:

- `ui_nav_student_card_01`
- `ui_nav_competency_card_01`
- `ui_nav_report_card_01`
- `ui_nav_subject_card_01`

## Erlaubte Praefixe

- `data_` fuer Workbook-Datenquellen und Tabellen
- `ui_` fuer UI-Anker und UI-Projektionen
- `ui_nav_` fuer navigierende Shapes
- `ui_dialog_` fuer worksheet-basierte Dialogseiten-Anker
- `frm_` fuer VBA-UserForms
- `ctl_` fuer technische UserForm-Control-Namen
- `ws` fuer Worksheet-CodeNames
- `Open` fuer zentrale VBA-Navigationsprozeduren

## Aktive Core-Referenzdaten

| Name | Zweck | Status |
| --- | --- | --- |
| `src/core/records.py` | Aktive leichte Dataclasses und deterministische Referenzdaten ohne Excel-Abhaengigkeit | aktiv |
| `StudentRecord` | read-only Kompatibilitaetsprojektion aus V3-Schuelerstammdaten und explizit aufgeloester Membership; kein Writer- oder Seedmodell | aktiv |
| `GroupRecord` | Dataclass fuer Stammgruppen-Referenzdaten | aktiv |
| `CourseRecord` | Dataclass fuer Kurs-Referenzdaten mit verbindlicher `year_level` 1, 2 oder 3 | aktiv |
| `ReferenceData` | Container fuer aktive Final-V4-Referenzdaten einschließlich historischer und aktueller Schuljahre sowie Assignments ohne Workbook-Bezug | aktiv |
| `seed_reference_data()` | Erzeugt deterministische Final-V4-Referenzdaten fuer explizite neue Seed-/Testpfade | aktiv |

Regel: Aktive Referenzdaten duerfen keine `openpyxl`- oder Workbook-Abhaengigkeit einfuehren.

## Verbotene technische Namen

Nicht erlaubt sind:

- technische Namen mit Umlauten
- technische Namen mit Leerzeichen
- sichtbare deutsche UI-Begriffe als technische Schluessel
- Namen, die mit Excel/VBA-Objekttypen kollidieren, zum Beispiel `shape`, `range`, `worksheet`, `name`, `index`
- neue kreative Praefixe ohne Registry-Erweiterung
- fachliche Anzeigenamen als technische Identitaet

## Navigationsprozeduren

Status: Legacy-/Export-Pfad. Bestehende VBA-Navigationsprozeduren bleiben dokumentiert, werden aber nicht fuer neue Features, UI, Smoke-Tests oder produktive Workflows erweitert.

Registriert:

- `OpenStudentProfileById(student_id)`
- `OpenClassOverview()`
- `ImportVbaSourcesToSeed(globalsPath, navigationPath, uiPath)`
- `ImportUserForm(formName, sourcePath)`

Vorgesehen:

- `OpenNewStudentDialog()` - deprecated UserForm-Testoeffner, nicht produktiver Feature-1-Einstieg
- `OpenCompetencyById(competency_id)`
- `OpenReportById(report_id)`
- `OpenSubjectById(subject_id)`

## Worksheet-basierte Dialogseiten

Status: Legacy. Worksheet-basierte Dialogseiten sind historische Artefakte der Excel-Linie. Neue Eingabedialoge werden fuer die PySide-Hauptanwendung dokumentiert und umgesetzt.

Registrierte Dialogseiten:

- `dlg_neuer_schueler`

Registrierte Anker fuer `dlg_neuer_schueler`:

- `ui_action_new_student`
- `ui_dialog_new_student_first_name`
- `ui_dialog_new_student_last_name`
- `ui_dialog_new_student_group`
- `ui_dialog_new_student_course`
- `ui_dialog_new_student_notes`
- `ui_dialog_new_student_document_list`
- `ui_dialog_new_student_add_document`
- `ui_dialog_new_student_cancel`
- `ui_dialog_new_student_save`

## SQLite-Spike

Registrierter Spike-Pfad:

- `data/kompetenzmanager.sqlite`

Registrierte SQLite-Tabellen:

- `students`
- `groups`
- `courses`
- `course_groups`
- `course_group_student_groups`
- `course_group_courses`
- `observations`
- `observation_competency_ratings`
- `competencies`
- `documents`

Registrierte Python-Spike-Komponenten:

- `SQLiteDatabase`
- `SQLiteStudentRepository`
- `SQLiteGroupRepository`
- `SQLiteCourseRepository`
- `SQLiteCompetencyRepository`
- `SQLiteStudentCompetencyConfirmationRepository`
- `SQLiteMasterDataRepository`
- `SQLiteObservationRepository`
- `SQLiteDocumentRepository`
- `MasterDataGroupRecord`
- `MasterDataCourseRecord`
- `MasterDataCourseGroupRecord`
- `CompetencyRecord`
- `StudentCompetencyConfirmationRecord`
- `DocumentRecord`
- `ObservationCompetencyRatingRecord`
- `ObservationRecord`
- `ObservationService`
- `ObservationValidator`
- `ObservationValidationError`
- `ObservationRepositoryError`
- `create_sqlite_seed_database(path)`
- `SQLiteDatabase.replace_seed_data(reference_data)`
- `SeedDataError`
- `SeedResult`
- `seed_test_data(database_path, reset)`
- `SeedResult.timetable_count`
- `_seed_timetable(database)`
- `_seed_all_subject_history(database, service, students)`

Regel: `create_sqlite_seed_database(path)` ist ein expliziter Final-V4-
Seed-/Testpfad für ein neues Ziel. Der produktive PySide-App-Start nutzt
diesen Pfad nicht, damit keine synthetischen Schüler erzeugt, keine
vorhandene Datenbank ersetzt und keine Nutzerdaten migriert werden.

Registrierte SQLite-/Stammdaten-Konstanten:

- `COLOR_NAME`
- `COLOR_HEX`
- `COURSE_GROUP_ID_PREFIX`
- `COURSE_COLOR_OPTIONS`
- `DEFAULT_COURSE_GROUP_ID`
- `DEFAULT_COURSE_GROUP_NAME`

Registrierte Stammdaten-Repository-Methoden:

- `SQLiteDatabase.ensure_master_data_defaults()`
- `SQLiteMasterDataRepository.list_student_groups()`
- `SQLiteMasterDataRepository.upsert_student_group(group, as_of=None)`
- `SQLiteMasterDataRepository.list_courses()`
- `SQLiteMasterDataRepository.upsert_course(course, as_of=None)`
- `SQLiteMasterDataRepository.list_course_groups()`
- `SQLiteMasterDataRepository.update_course_group(course_group)`
- `SQLiteMasterDataRepository.get_course_group_relations(course_group_id)`
- `SQLiteMasterDataRepository.replace_course_group_student_groups(course_group_id, group_ids)`
- `SQLiteMasterDataRepository.replace_course_group_courses(course_group_id, course_ids)`
- `SQLiteMasterDataRepository.next_student_group_id()`
- `SQLiteMasterDataRepository.next_course_id()`
- `SQLiteMasterDataRepository.next_course_group_id()`
- `SQLiteObservationRepository.create_observation(observation)`
- `SQLiteObservationRepository.update_observation(observation)`
- `SQLiteObservationRepository.deactivate_observation(observation_id, updated_at)`
- `SQLiteObservationRepository.list_observations()`
- `SQLiteObservationRepository.list_observations_for_student(student_id)`
- `SQLiteObservationRepository.get_observation(observation_id)`
- `SQLiteCompetencyRepository.ensure_catalog_defaults(entries)`
- `SQLiteCompetencyRepository.list_competencies()`
- `SQLiteCompetencyRepository.get_competency(competency_id)`
- `SQLiteStudentCompetencyConfirmationRepository.list_confirmations_for_student(student_id)`
- `SQLiteStudentCompetencyConfirmationRepository.get_confirmation(student_id, competency_id)`
- `SQLiteStudentCompetencyConfirmationRepository.upsert_confirmation(confirmation)`
- `SQLiteDocumentRepository.create_document(document)`
- `SQLiteDocumentRepository.list_documents_for_student(student_id)`
- `SQLiteDocumentRepository.list_documents_for_observation(observation_id)`
- `SQLiteDocumentRepository.deactivate_document(document_id)`
- `SQLiteDocumentRepository.next_document_id()`

Registrierte Spike-Skripte:

- `scripts/create_sqlite_spike.py`
- `scripts/seed_test_data.py`

Registrierte interne QS-Skripte fuer den Kompetenzkatalog:

- `scripts/validate_curriculum_catalog.py`
- `scripts/compare_curriculum_catalog.py`
- `scripts/next_competency_ids.py`
- `scripts/curriculum_catalog_tools.py`

## Application Command Layer

Registrierte Python-Module:

- `src/application/dispatcher.py`
- `src/application/commands/observation.py`
- `src/application/commands/report.py`

Registrierte Python-Klassen und Funktionen:

- `ApplicationCommandDispatcher`
- `CommandDispatchError`
- `CommandHandler`
- `SuccessResult`
- `ErrorResult`
- `CreateObservationCommand`
- `UpdateObservationCommand`
- `DeleteObservationCommand`
- `observation_create_handler(service)`
- `observation_update_handler(service)`
- `observation_delete_handler(service)`

Registrierte Command-Namen:

- `observation.create`
- `observation.update`
- `observation.delete`

Seit SJ-2F sind `src/application/commands/student.py`,
`CreateStudentCommand` und `student_create_handler` keine registrierten
Produktnamen mehr. Die Student-Writer verwenden die getrennten
V3-Lifecycles aus dem Schuljahres- und Assignmentregister.

## Desktop-App

Status:

PySide ist die Hauptanwendung. Der Desktop-App-Layer bleibt Adapter/UI-Schicht und greift nicht direkt aus Widgets auf SQLite zu.

Registrierte Katalogdateien:

- `data/curriculum_catalog_v1.csv`

Registrierte Python-Module:

- `assets/app_icon.png`
- `src/desktop_app/main.py`
- `src/desktop_app/app.py`
- `src/desktop_app/assets.py`
- `src/desktop_app/shell.py`
- `src/desktop_app/navigation.py`
- `src/desktop_app/theme.py`
- `src/desktop_app/student_adapter.py`
- `src/desktop_app/student_list_view.py`
- `src/desktop_app/new_student_dialog.py`
- `src/desktop_app/adapters/curriculum_desktop_adapter.py`
- `src/desktop_app/adapters/master_data_desktop_adapter.py`
- `src/desktop_app/adapters/student_desktop_adapter.py`
- `src/desktop_app/dialogs/app_info_dialog.py`
- `src/desktop_app/dialogs/dialog_buttons.py`
- `src/desktop_app/dialogs/master_data_dialog.py`
- `src/desktop_app/dialogs/new_observation_dialog.py`
- `src/desktop_app/dialogs/new_student_dialog.py`
- `src/desktop_app/components.py`
- `src/desktop_app/icons.py`
- `src/desktop_app/screens/master_data_screen.py`
- `src/desktop_app/screens/overview_screen.py`
- `src/desktop_app/screens/students_screen.py`
- `src/desktop_app/screens/students_workspace.py`
- `src/desktop_app/screens/student_profile_screen.py`
- `src/desktop_app/screens/placeholder_screen.py`
- `src/desktop_app/view_models/master_data_view_model.py`
- `src/desktop_app/view_models/observation_view_model.py`
- `src/desktop_app/view_models/student_view_model.py`

Registrierte Launcher:

- `launcher/Jenaplan_Kompetenzmanager.command`

Registrierte Python-Klassen und Funktionen:

- `JenaplanDesktopApp`
- `AppShell`
- `NavigationItem`
- `NavigationTarget`
- `NAVIGATION_ITEMS`
- `resolve_navigation_target(key)`
- `APP_ICON_RELATIVE_PATH`
- `project_root()`
- `app_icon_path()`
- `load_app_icon_pixmap(size)`
- `create_app_icon_label(size)`
- `apply_app_theme(app)`
- `APP_STYLESHEET`
- `PRIMARY_BUTTON_STYLESHEET`
- `create_card()`
- `set_label_style(label, role)`
- `set_button_role(button, role)`
- `ObservationFilterBar`
- `ObservationFilterInput`
- `ObservationTextActionButton`
- `ObservationResetButton`
- `NewObservationDialog.subject_options`
- `QDateEdit`
- `QDateTimeEdit`
- `QTimeEdit`
- `COLOR_NAVY`
- `COLOR_BLUE`
- `COLOR_TURQUOISE`
- `COLOR_GREEN`
- `COLOR_ORANGE`
- `StudentDesktopAdapter`
- `StudentDesktopAdapter.list_students(group_id, group_ids, course_id)`
- `StudentDesktopAdapter.create_update_observation_command(draft)`
- `StudentDesktopAdapter.update_observation(draft)`
- `StudentDesktopAdapter.delete_observation(observation_id)`
- `StudentDesktopAdapter.observation_draft_for_edit(observation_id)`
- `StudentDesktopAdapter.list_competency_overview_for_student(student_id)`
- `StudentDesktopAdapter.list_competency_status_projection_for_student(student_id)`
- `StudentDesktopAdapter.competency_cockpit_for_student(student_id)`
- `StudentDesktopAdapter.list_documentation_status_for_student(student_id)`
- `StudentDesktopAdapter.list_documents_for_student(student_id)`
- `StudentDesktopAdapter.add_student_document(student_id, source_path, document_type, title, note, observation_id)`
- `StudentDesktopAdapter.remove_document(document_id)`
- `StudentDesktopAdapter.get_report_preview_for_student(student_id)`
- `StudentDesktopAdapter.settings_view_model()`
- `StudentDesktopAdapter.list_documentation_subject_options()`
- `StudentDesktopAdapter.list_observation_subject_options(initial_draft)`
- `StudentDesktopAdapter.list_observation_competency_subject_groups(initial_draft)`
- `StudentDesktopAdapter.save_active_documentation_subjects(subject_ids)`
- `StudentDesktopAdapter._active_documentation_subject_ids()`
- `StudentDesktopAdapter._initial_observation_subject_key(initial_draft)`
- `StudentDesktopAdapter._initial_observation_subject_label(initial_draft)`
- `StudentDesktopAdapter._documentation_relevant_competencies()`
- `StudentDesktopAdapter._report_development_line(competency)`
- `StudentDesktopAdapter._report_development_label(rating_history)`
- `StudentDesktopAdapter._is_monotonic(scores, increasing)`
- `StudentDesktopAdapter.save_competency_confirmation(student_id, competency_id, confirmed_rating, note)`
- `StudentCompetencyStatusViewModel.documentation_state`
- `StudentCompetencyStatusViewModel.observed_proposal`
- `StudentCompetencyStatusViewModel.documentation_state_label`
- `StudentCompetencyStatusViewModel.confirmed_status_label`
- `StudentCompetencyEvidenceViewModel`
- `StudentCompetencyCockpitViewModel`
- `StudentCompetencyCockpitSubjectViewModel`
- `StudentCompetencyCockpitLearningAreaViewModel`
- `StudentCompetencyCockpitTopicViewModel`
- `build_student_competency_cockpit(statuses)`
- `StudentProfileDashboardViewModel`
- `StudentProfileProjectionBundle`
- `StudentProfileOrientationChangeViewModel`
- `StudentProfileOrientationEventViewModel`
- `StudentProfileUndocumentedSubjectViewModel`
- `build_student_profile_dashboard(statuses, documentation_statuses, as_of)`
- `StudentDesktopAdapter.student_profile_dashboard_for_student(student_id, as_of)`
- `StudentDesktopAdapter.student_profile_projection_bundle(student_id)`
- `StudentDocumentationLearningAreaStatus`
- `SettingsScreen`
- `SettingsScreen.documentation_subjects_save_requested`
- `SettingsScreen.set_settings(view_model)`
- `SettingsScreen.set_documentation_subjects(subjects)`
- `SettingsScreen.show_documentation_subjects_saved()`
- `DocumentationSubjectSettingsSection`
- `DocumentationSubjectCheckbox_{subject_id}`
- `DocumentationSubjectSaveButton`
- `SettingsStatusLabel`
- `DOCUMENTATION_SUBJECTS_HELP_TEXT`
- `DOCUMENTATION_SUBJECTS_SAVE_SUCCESS_MESSAGE`
- `StudentProfileScreen.DEFAULT_OBSERVATION_LIMIT`
- `StudentProfileScreen.apply_observation_filters()`
- `StudentProfileScreen.reset_observation_filters()`
- `StudentProfileScreen.toggle_observation_limit()`
- `StudentProfileScreen._populate_observation_subject_filter(observations)`
- `StudentProfileScreen._filtered_observations()`
- `StudentProfileScreen._visible_observations(observations)`
- `StudentProfileScreen._update_observation_limit_action(observations)`
- `StudentProfileScreen._observation_filter_is_active()`
- `StudentProfileScreen._matches_observation_filters(observation, subject_filter, rating_filter, search_text)`
- `StudentProfileScreen._observation_search_text(observation)`
- `StudentProfileScreen._observation_summary(observation)`
- `StudentProfileScreen._toggle_observation_details(details_widget, details_button)`
- `StudentProfileScreen._observation_actions(observation)`
- `StudentProfileScreen._note_preview(note, max_length)`
- `StudentProfileScreen.set_competency_cockpit(cockpit)`
- `StudentProfileScreen.apply_competency_cockpit_filters()`
- `StudentProfileScreen.reset_competency_cockpit_filters()`
- `StudentProfileScreen._populate_competency_subject_filter(cockpit)`
- `StudentProfileScreen._filtered_cockpit_subject(subject, documentation_filter, learning_stage_filter, search_text)`
- `StudentProfileScreen._filtered_cockpit_learning_area(area, documentation_filter, learning_stage_filter, search_text)`
- `StudentProfileScreen._matches_competency_documentation_filter(competency, documentation_filter)`
- `StudentProfileScreen._cockpit_subject_card(subject, historical)`
- `StudentProfileScreen._cockpit_learning_area_card(subject_id, area, historical)`
- `StudentProfileScreen._cockpit_topic_card(subject_id, learning_area, topic, historical)`
- `StudentProfileScreen._cockpit_competency_row(competency)`
- `StudentProfileScreen._cockpit_competency_details(competency)`
- `StudentProfileScreen._make_clickable_card(card, action, tooltip)`
- `StudentProfileScreen._historical_competency_section(subjects)`
- `StudentProfileScreen._toggle_cockpit_section(key, details, button, collapsed_text, expanded_text)`
- `StudentProfileScreen._show_observations_tab()`
- `StudentProfileScreen._documentation_subject_details(status)`
- `StudentProfileScreen._toggle_documentation_status_details(details_container, details_button)`
- `StudentProfileScreen.set_documents(documents)`
- `StudentProfileScreen._documents_card()`
- `StudentProfileScreen._empty_documents_card()`
- `StudentProfileScreen._document_row(document)`
- `StudentProfileScreen.document_remove_requested(student_id, document_id)`
- `StudentProfileScreen._request_document_remove(document_id)`
- `StudentProfileScreen.open_document_file(file_path)`
- `StudentProfileScreen._observation_attachments_block(observation)`
- `StudentProfileScreen.set_report_preview(report_preview)`
- `StudentProfileScreen._report_subject_card(section)`
- `StudentProfileScreen._report_bucket(title, competencies)`
- `StudentProfileScreen._report_evidence_block(observations)`
- `StudentProfileScreen.report_text()`
- `StudentProfileScreen.copy_report_text_to_clipboard()`
- `StudentProfileScreen.export_report_text()`
- `StudentProfileScreen.export_report_text_to_path(target_path)`
- `StudentProfileScreen._default_report_export_filename()`
- `CompetencyCockpitSubjectCard`
- `CompetencyCockpitFilterBar`
- `CompetencyCockpitSubjectFilter`
- `CompetencyCockpitDocumentationFilter`
- `CompetencyCockpitFilterResetButton`
- `CompetencyCockpitEmptyFilterState`
- `CompetencyCockpitSubjectButton`
- `CompetencyCockpitSubjectDetails`
- `CompetencyCockpitLearningAreaCard`
- `CompetencyCockpitLearningAreaButton`
- `CompetencyCockpitLearningAreaDetails`
- `CompetencyCockpitTopicCard`
- `CompetencyCockpitTopicButton`
- `CompetencyCockpitTopicDetails`
- `CompetencyCockpitCompetencyRow`
- `CompetencyCockpitCompetencyButton`
- `CompetencyCockpitCompetencyDetails`
- `CompetencyCockpitObservationsButton`
- `CompetencyCockpitHistoricalCard`
- `CompetencyCockpitHistoricalButton`
- `CompetencyCockpitHistoricalDetails`
- `CompetencyCockpitProgressBar`
- `MasterDataDesktopAdapter`
- `MasterDataDesktopAdapter.add_course_group(name, selected_group_ids, selected_course_ids)`
- `MasterDataDesktopAdapter.update_course_group(course_group_id, name, selected_group_ids, selected_course_ids)`
- `CurriculumDesktopAdapter`
- `CurriculumCatalogEntry`
- `CurriculumCompetencyGroup`
- `CurriculumSubjectOption`
- `CATALOG_REQUIRED_FIELDS`
- `CURRICULUM_CATALOG_V1_PATH`
- `CurriculumCatalogEntry.competency_id`
- `CurriculumCatalogEntry.sort_order`
- `CurriculumCatalogEntry.subject_id`
- `CurriculumCatalogEntry.competency_display_name`
- `CurriculumCatalogEntry.competency_detail_label`
- `StudentListItem`
- `StudentListItem.documentation_status`
- `StudentDetailViewModel`
- `StudentDetailViewModel.course_color_name`
- `StudentDetailViewModel.course_color_hex`
- `DashboardSuggestedStudentViewModel.course_name`
- `DashboardSuggestedStudentViewModel.course_color_name`
- `DashboardSuggestedStudentViewModel.course_color_hex`
- `GroupSummaryViewModel`
- `StudentReportCompetencyViewModel`
- `StudentReportDevelopmentViewModel`
- `StudentReportEvidenceViewModel`
- `StudentReportSubjectSectionViewModel`
- `StudentReportSubjectSectionViewModel.current_statuses`
- `StudentReportPreviewViewModel`
- `StudentDocumentViewModel`
- `StudentDocumentViewModel.display_title`
- `StudentDocumentViewModel.created_date_label`
- `StudentDocumentViewModel.observation_link_label`
- `format_student_report_preview_text(student, report_preview, created_date)`
- `MasterDataItemViewModel`
- `MasterDataViewModel`
- `CourseGroupViewModel`
- `SettingsViewModel`
- `DocumentationSubjectOptionViewModel`
- `normalize_master_data_name(name)`
- `course_color_from_key(color_key, fallback_index)`
- `course_color_name(color_hex)`
- `COURSE_COLOR_OPTIONS`
- `CourseBadge`
- `CourseBadge.set_course(course_name, color_hex)`
- `CourseBadgeIndicator`
- `CourseBadgeLabel`
- `semanticRole = courseContext`
- `courseColorHex`
- `usesNeutralColor`
- `COURSE_GROUP_EMPTY_GROUPS_MESSAGE`
- `COURSE_GROUP_EMPTY_COURSES_MESSAGE`
- `COURSE_GROUP_DUPLICATE_NAME_MESSAGE`
- `MASTER_DATA_EMPTY_NAME_MESSAGE`
- `MASTER_DATA_SAVE_PLACEHOLDER_MESSAGE`
- `filter_student_list(students, search_text)`
- `sort_student_list(students, course_order_by_id)`
- `PROFILE_ACTION_MESSAGES`
- `PROFILE_SECTION_PLACEHOLDERS`
- `ObservationCompetencyRatingDraft`
- `ObservationCompetencyRatingDraft.competency_id`
- `ObservationCompetencyRatingDraft.subject_display_name`
- `ObservationSubjectOptionViewModel`
- `ObservationCompetencySubjectGroupViewModel`
- `ObservationCompetencySubjectGroupViewModel.subject_key`
- `ObservationCompetencySubjectGroupViewModel.subject_display_name`
- `ObservationCompetencySubjectGroupViewModel.learning_area_groups`
- `ObservationLearningAreaGroupViewModel`
- `ObservationLearningAreaGroupViewModel.learning_area`
- `ObservationLearningAreaGroupViewModel.competency_groups`
- `ObservationCompetencyGroupViewModel`
- `ObservationCompetencyGroupViewModel.competency_group`
- `ObservationCompetencyGroupViewModel.competencies`
- `ObservationCompetencyOptionViewModel`
- `ObservationCompetencyOptionViewModel.competency_id`
- `ObservationCompetencyOptionViewModel.subject_key`
- `ObservationCompetencyOptionViewModel.subject_display_name`
- `ObservationCompetencyOptionViewModel.learning_area`
- `ObservationCompetencyOptionViewModel.competency_group`
- `ObservationCompetencyOptionViewModel.competency_text`
- `ObservationCompetencyOptionViewModel.competency_label`
- `ObservationCompetencyOptionViewModel.selected`
- `ObservationCompetencyOptionViewModel.rating`
- `ObservationCompetencyOptionViewModel.learning_stage`
- `ObservationCompetencyOptionViewModel.catalog_status`
- `ObservationCompetencyOptionViewModel.is_active`
- `ObservationCompetencyOptionViewModel.sort_order`
- `StudentDesktopAdapter.list_recent_observation_competencies(student_id, initial_draft)`
- `NewObservationDialog.recent_competencies`
- `NewObservationDialog.recent_competency_chips`
- `ObservationRecentCompetencies`
- `ObservationRecentCompetencyChip`
- `ObservationRatingSelector`
- `ObservationRatingSelector.FULL_LABEL_MINIMUM_WIDTH`
- `ObservationRatingSelector.resizeEvent(event)`
- `ObservationCatalogCompetencyTile`
- `NewObservationDialog.competency_catalog_tiles`
- `ObservationThreeZoneWorkspace`
- `ObservationSelectedScroll`
- `ObservationCatalogScroll`
- `ObservationAttachmentsScroll`
- `ObservationPersistentActions`
- `ObservationAttachmentDraft`
- `ObservationAttachmentDraft.display_label`
- `ObservationDraftViewModel`
- `ObservationDraftViewModel.observation_id`
- `ObservationDraftViewModel.subject_id`
- `ObservationDraftViewModel.subject_display_name`
- `ObservationDraftViewModel.attachments`
- `ObservationListItem`
- `ObservationListItem.attachments`
- `ObservationRatingViewModel`
- `StudentCompetencyStatusViewModel`
- `StudentCompetencyStatusViewModel.rating_history`
- `StudentCompetencyStatusViewModel.observation_count`
- `StudentCompetencyStatusViewModel.weighted_score`
- `StudentCompetencyStatusViewModel.confirmed_rating`
- `StudentCompetencyStatusViewModel.confirmed_at`
- `StudentCompetencyStatusViewModel.confirmation_note`
- `StudentCompetencyStatusViewModel.rating_history_label`
- `StudentCompetencyStatusViewModel.observation_count_label`
- `StudentCompetencyStatusViewModel.confirmation_status_label`
- `StudentCompetencyStatusViewModel.confirmation_meta_label`
- `StudentCompetencySubjectGroup`
- `StudentCompetencySubjectGroup.missing_competencies`
- `StudentDocumentationSummaryViewModel`
- `StudentDocumentationSummaryViewModel.list_label`
- `StudentDocumentationSummaryViewModel.profile_summary_label`
- `StudentDocumentationSummaryViewModel.weak_subjects_label`
- `documentation_summary_from_subjects(statuses)`
- `empty_documentation_summary()`
- `REPORT_NO_OBSERVATIONS_MESSAGE`
- `StudentDocumentationSubjectStatus`
- `StudentDocumentationSubjectStatus.progress_label`
- `StudentDocumentationSubjectStatus.missing_count_label`
- `StudentMissingCompetencyViewModel`
- `OBSERVATION_CONTEXT_OPTIONS`
- `OBSERVATION_CROSS_SUBJECT_LABEL`
- `OBSERVATION_RATING_OPTIONS`
- `OBSERVATION_SAVE_SUCCESS_MESSAGE`
- `OBSERVATION_UPDATE_SUCCESS_MESSAGE`
- `OBSERVATION_SAVE_VALIDATION_MESSAGE`
- `OBSERVATION_ATTACHMENT_EMPTY_STATE`
- `DOCUMENT_TYPE_OPTIONS`
- `observation_rating_label(rating)`
- `calculated_rating_from_history(ratings_newest_first)`
- `rating_from_weighted_score(score)`
- `observation_rating_keys()`
- `DIALOG_CANCEL_TEXT`
- `DIALOG_SAVE_TEXT`
- `configure_save_cancel_buttons(buttons)`
- `AppShell.refresh_overview()`
- `AppShell.show_students_for_course_group(course_group_id, course_id)`
- `AppShell.open_new_course_group_dialog()`
- `AppShell.open_edit_course_group_dialog(course_group_id)`
- `AppShell.remove_student_document(student_id, document_id)`
- `GroupOverviewScreen.set_master_data(view_model, group_summaries)`
- `OVERVIEW_GROUP_EMPTY_STATE`
- `OVERVIEW_COURSE_EMPTY_STATE`
- `MASTER_DATA_COURSE_GROUP_EMPTY_STATE`
- `MasterDataScreen.course_group_add_requested`
- `MasterDataScreen._activate_table_row(table, row)`
- `APP_INFO_TITLE`
- `APP_INFO_APP_NAME`
- `APP_INFO_MODE`
- `APP_INFO_DEVELOPER_NAME`
- `APP_INFO_DESCRIPTION`
- `APP_INFO_COPYRIGHT`
- `STUDENT_SEARCH_PLACEHOLDER`
- `STUDENT_LIST_EMPTY_STATE`
- `STUDENT_SEARCH_EMPTY_STATE`
- `MASTER_DATA_GROUP_EMPTY_STATE`
- `MASTER_DATA_COURSE_EMPTY_STATE`
- `STUDENT_DIALOG_SELECT_PLACEHOLDER`
- `STUDENT_DIALOG_EMPTY_NAME_MESSAGE`
- `STUDENT_DIALOG_GROUP_REQUIRED_MESSAGE`
- `STUDENT_DIALOG_COURSE_REQUIRED_MESSAGE`
- `STUDENT_DIALOG_DRAFT_GROUP_MESSAGE`
- `STUDENT_DIALOG_DRAFT_COURSE_MESSAGE`
- `StudentListView`
- `OverviewScreen`
- `StudentsScreen`
- `StudentsWorkspace`
- `StudentsScreen.observation_requested`
- `StudentsScreen.back_to_overview_requested`
- `StudentProfileScreen`
- `StudentProfileScreen.profile_tabs`
- `StudentProfileOverviewViewModel`
- `build_student_profile_overview(observations, competency_groups, documentation_statuses)`
- `MasterDataScreen`
- `PlaceholderScreen`
- `AppInfoDialog`
- `CourseGroupDialog`
- `MasterDataNameDialog`
- `NewObservationDialog`
- `NewStudentDialog`
- `AppShell.open_quick_observation_dialog(student_id)`
- `AppShell.return_to_overview()`
- `main()`

Regel:

Der Desktop-App-Layer ist Adapter/UI-Schicht. Er darf Daten anzeigen, Eingaben sammeln, Commands oder Repository-Aufrufe ueber freigegebene Adapter ausloesen. Er darf keine Businesslogik enthalten, keine Schueler-IDs erzeugen und nicht direkt aus Qt-Widgets in SQLite schreiben.

## Runtime Adapter und Projection Refresh

Status: Historischer Excel/VBA-Bridge-Pfad unter `legacy/excel/`. Nicht Teil aktiver PySide-Standardchecks.

Historisch umgesetzte VBA-Adapter-Prozeduren:

- `SaveNewStudentDialog()`

Vorgesehene VBA-Adapter-Prozeduren:

- `CancelNewStudentDialog()`
- `ImportProjectionRefresh()`

Historisch umgesetzte Python-CLI/Bridge:

- `legacy/excel/km.py`
- `student create`

Historisch umgesetzte Runtime-Artefakte:

- `runtime_command.json`
- `runtime_result.json`

Vorgesehene Runtime-Artefakte:

- `runtime_projection_refresh.json`

Registrierte VBA-Konstanten fuer `dlg_neuer_schueler`:

- `NAME_DIALOG_NEW_STUDENT_FIRST_NAME`
- `NAME_DIALOG_NEW_STUDENT_LAST_NAME`
- `NAME_DIALOG_NEW_STUDENT_GROUP`
- `NAME_DIALOG_NEW_STUDENT_COURSE`
- `NAME_DIALOG_NEW_STUDENT_NOTES`
- `NAME_DIALOG_NEW_STUDENT_SAVE`
- `SHAPE_DIALOG_NEW_STUDENT_SAVE`
- `RUNTIME_COMMAND_FILE_NAME`
- `RUNTIME_RESULT_FILE_NAME`
- `RUNTIME_DATABASE_RELATIVE_PATH`

Regel:

Runtime-Artefakte enthalten keine neue fachliche Source of Truth.

Sie transportieren Commands, Ergebnisse oder Python-generierten Projection Output.

VBA darf Projection-Refresh-Artefakte nur in registrierte Projektionsbereiche kopieren.

## UserForms

Status:

VBA-UserForms sind ab Feature 1 fuer Excel auf macOS deprecated und nicht mehr das primaere Eingabe-Pattern.

`frm_student_new` bleibt als experimenteller Artefaktstand erhalten, bis ein eigener Bereinigungssprint das Artefakt entfernt oder migriert.

Registrierte UserForm-Namen:

- `frm_student_new`

Vorgesehene UserForm-Namen:

- `frm_observation_new`

Registrierte Control-Namen fuer `frm_student_new`:

- `ctl_first_name_label`
- `ctl_first_name`
- `ctl_last_name_label`
- `ctl_last_name`
- `ctl_group_id_label`
- `ctl_group_id`
- `ctl_course_id_label`
- `ctl_course_id`
- `ctl_student_notes_label`
- `ctl_student_notes`
- `ctl_document_section_label`
- `ctl_document_empty_state`
- `ctl_document_list`
- `ctl_add_document`
- `ctl_cancel`
- `ctl_save`

Vorgesehene Control-Namen fuer `frm_observation_new`:

- `ctl_observation_date`
- `ctl_observation_context`
- `ctl_competency_selection`
- `ctl_rating`
- `ctl_observation_note`
- `ctl_media_list`
- `ctl_add_media`

## VBA-Module

Status: Legacy-Archiv unter `legacy/excel/vba/`.

Registrierte Standardmodule im historischen Seed:

- `Globals`
- `Navigation`
- `UI`
- `SeedImport`

`SeedImport` war das Bootstrap-Modul fuer den automatischen Import versionierter `.bas`-Quellen in die historische Seed-Arbeitsmappe unter `legacy/excel/seeds/`.

## Sprint 7F - Produktiver Lernentwicklungsbericht

Registrierte Python-Module:

- `src/desktop_app/dialogs/learning_report_dialog.py`
- `src/desktop_app/view_models/learning_report_view_model.py`

Registrierte technische Namen:

- `PrepareLearningReportQuery`
- `LearningReportSourceData`
- `LearningReportApplicationService`
- `LearningReportPreparationViewModel`
- `LearningReportSubjectViewModel`
- `LearningReportCompetencyViewModel`
- `LearningReportEvidenceViewModel`
- `LearningReportDraft`
- `LearningReportDialog`
- `LearningReportDraftSelectionDialog`
- `LearningReportDraftChoice_<report_draft_id>`
- `StudentDesktopAdapter.learning_report_preparation_for_student(student_id, retained_competency_ids=())`
- `build_learning_report_preparation(student, statuses, observations)`
- `build_report_output_model(preparation, draft)`
- `AppShell.open_learning_report_dialog(student_id)`
- `AppShell.export_learning_report_pdf(output_model)`

Regel: Diese Namen bezeichnen ausschliesslich die fluechtige Berichtsvorbereitung und das neutrale Ausgabemodell. Sie fuehren keine persistente Berichtsentitaet und keine zweite Kompetenzstatuslogik ein.

Registrierte Qt-Objektnamen fuer das Sprint-7F.1-UX-Alignment:

- `LearningReportWorkspace`
- `LearningReportTopBar`
- `LearningReportBrand`
- `LearningReportTopHint`
- `LearningReportEyebrow`
- `LearningReportStatusPill`
- `LearningReportInternalCard`
- `LearningReportResponsibilityNote`
- `LearningReportPreviewPanel`
- `LearningReportPreviewScroll`
- `LearningReportPreviewCanvas`
- `LearningReportPaperPage`
- `LearningReportDocumentBlock`

## Sprint 7F.1 - Persistenter Berichtsentwurf

Registrierte Python-Module:

- `src/core/report_draft.py`
- `tests/test_report_draft.py`

Registrierte Klassen und Application-Namen:

- `ReportDraftRecord`
- `ReportDraftSubjectRecord`
- `ReportDraftChartSelectionRecord`
- `ReportDraftRepository`
- `SQLiteReportDraftRepository`
- `ReportDraftService`
- `ReportDraftApplicationService`
- `CreateLearningReportDraftCommand`
- `UpdateLearningReportDraftCommand`
- `GetLearningReportDraftQuery`
- `ListLearningReportDraftsQuery`
- `LearningReportDraftViewModel`
- `LearningReportSubjectDraftViewModel`
- `LearningReportChartSelectionViewModel`
- `StudentDesktopAdapter.save_learning_report_draft(draft)`
- `StudentDesktopAdapter.load_learning_report_draft(report_draft_id)`
- `StudentDesktopAdapter.list_learning_report_drafts_for_student(student_id)`

Registrierte Konstanten:

- `REPORT_DRAFT_ID_PREFIX`
- `REPORT_DRAFT_STATUS`
- `LEARNING_DEVELOPMENT_REPORT_TYPE`
- `REPORT_DRAFT_CHART_TYPES`

Regel: Der persistente Entwurf ist ein bearbeitbarer Arbeitsstand. Er ist kein `ReportOutputModel`, keine finale Berichtsversion und keine Quelle fuer Kompetenzstatus oder Beobachtungsbewertung.

## Sprint 7F.2 - Prototypgetreue Berichtswerkstatt

Registrierte technische Namen:

- `LearningReportDialog.save_requested`
- `LearningReportDialog.report_draft_view_model()`
- `LearningReportDialog.apply_saved_draft(saved)`
- `CHART_OPTIONS`
- `LearningReportModeButton`
- `LearningReportSidebar`
- `LearningReportSubjectButton`
- `LearningReportInternalBadge`
- `LearningReportReportCard`

Regel: Diese Namen bilden ausschliesslich die aus `prototypes/learning_report_ux/` portierte PySide-Navigation, Kartenhierarchie, Draft-Anbindung und Auswahl der bereits registrierten Diagrammtypen ab. `LearningReportDraftSelectionDialog` ist eine lokale Qt-Komposition: Bei mindestens einem vorhandenen Entwurf wählt sie bewusst einen gespeicherten RPD oder den neuen, noch ungespeicherten Arbeitsstand. Sie fuehrt keine neue Datenquelle, keine Kompetenzstatuslogik und keinen zusaetzlichen Schreibprozess ein.

## Sprint 5B.1 - Bestandssichere Berichtreferenzen

Registrierte Lese- und Projektionsnamen:

- `LearningReportDraftViewModel.unavailable_observation_ids`
- `LearningReportDraft.unavailable_observation_ids`
- `SQLiteReportDraftRepository.unavailable_observation_ids(draft)`
- `StudentDesktopAdapter._learning_report_draft_view_model(record)`
- `_unavailable_evidence_blocks(draft)`
- `LearningReportDialog._unavailable_evidence_card()`
- `LearningReportUnavailableEvidence`
- `LearningReportUnavailableEvidence_<observation_id>`

Regel: `retained_competency_ids` erweitert fuer einen geladenen Berichtsdraft ausschliesslich den Lesekontext der bestehenden kanonischen Kompetenzprojektion. `unavailable_observation_ids` ist eine abgeleitete Kennzeichnung bereits gespeicherter, nicht mehr aktiver `OBS`-Referenzen und kein persistiertes Fachfeld. Beide Pfade erhalten bestehende IDs, erlauben keine neue Auswahl inaktiver Quellen und erzeugen weder Snapshottexte noch eine zweite Kompetenzstatuslogik.

## Sprint 5B.2 - Unveraenderliche Berichtrevisionen

Registrierte Python-Module:

- `src/core/learning_report.py`
- `tests/test_report_finalization.py`

Registrierte Klassen, Protokolle und Funktionen:

- `LearningReportRecord`
- `LearningReportRevisionRecord`
- `LearningReportFinalizationSource`
- `LearningReportRepository`
- `LearningReportSnapshotBuilder`
- `LearningReportFinalizationValidator`
- `ReportFinalizationService`
- `ReportFinalizationError`
- `FinalizeLearningReportCommand`
- `ReportFinalizationApplicationService`
- `canonical_snapshot_json(snapshot)`
- `snapshot_sha256(canonical_json)`
- `SQLiteLearningReportRepository`

Registrierte Konstanten und Werte:

- `LEARNING_REPORT_ID_PREFIX` mit Wert `RPT`
- `LEARNING_REPORT_REVISION_ID_PREFIX` mit Wert `RPV`
- `LEARNING_REPORT_SNAPSHOT_SCHEMA_VERSION` mit Wert `1`
- Revisionsstatus `finalized`
- Revisionsstatus `superseded`

Regel: `RPD` bleibt der bearbeitbare Arbeitsentwurf. `RPT` ist das stabile, pro `source_report_draft_id` eindeutige Berichtaggregat. Nach Revision 1 bleiben `source_report_draft_id`, `student_id`, `report_type`, `period_start` und `period_end` des `RPT` unveraenderlich; ein anderer Berichtstyp oder Zeitraum braucht einen neuen `RPD` und damit ein neues `RPT`. `RPV` ist eine unveraenderliche Revision; ausschliesslich beim atomaren Erzeugen einer Folgerevision darf der Status der bisherigen aktuellen Revision von `finalized` auf `superseded` wechseln und `superseded_at` gesetzt werden. Der kanonische Snapshot wird als UTF-8-JSON mit sortierten Schluesseln, kompakten Trennern und ohne nicht endliche Zahlen serialisiert; `snapshot_sha256` ist der kleingeschriebene SHA-256-Hexdigest exakt dieser gespeicherten JSON-Bytes.

## Sprint 5B.3 - Produktive Berichtfinalisierung und Revisionsprojektion

Registrierte Klassen und Projektionen:

- `LearningReportFinalizationPreview`
- `LearningReportRevisionState`
- `LearningReportRevisionReadService`
- `ReportRevisionApplicationService`
- `LearningReportRevisionStatusViewModel`
- `LearningReportRevisionHistoryItemViewModel`
- `LearningReportFinalizationPreviewViewModel`
- `LearningReportRevisionViewModel`
- `LearningReportRevisionSubjectViewModel`
- `LearningReportRevisionCompetencyViewModel`
- `LearningReportRevisionObservationViewModel`
- `LearningReportRevisionChartViewModel`
- `LearningReportRevisionDialog`

Registrierte Funktionen und Adapteroperationen:

- `ReportFinalizationService.prepare(report_draft_id)`
- `LearningReportRevisionReadService.report_for_draft(report_draft_id)`
- `LearningReportRevisionReadService.current_revision_for_draft(report_draft_id)`
- `LearningReportRevisionReadService.revision_history_for_draft(report_draft_id)`
- `LearningReportRevisionReadService.revision_by_id(learning_report_revision_id)`
- `LearningReportRevisionReadService.snapshot_hash_valid(revision)`
- `LearningReportRevisionReadService.snapshot_payload(learning_report_revision_id)`
- `SQLiteLearningReportRepository.get_revision(learning_report_revision_id)`
- `StudentDesktopAdapter.learning_report_revision_status(report_draft_id)`
- `StudentDesktopAdapter.prepare_learning_report_finalization(report_draft_id)`
- `StudentDesktopAdapter.finalize_learning_report(report_draft_id, finalized_by_display_name)`
- `StudentDesktopAdapter.load_learning_report_revision(learning_report_revision_id)`
- `build_learning_report_revision_status(state)`
- `build_learning_report_finalization_preview(preview)`
- `build_learning_report_revision_view_model(revision, payload)`

Registrierte Qt-Objektnamen:

- `LearningReportFinalizeButton`
- `LearningReportOpenCurrentRevisionButton`
- `LearningReportOpenRevision_<learning_report_revision_id>`
- `LearningReportFinalizationConfirmation`
- `LearningReportFinalizedByInput`
- `LearningReportFinalizationAcknowledgement`
- `LearningReportFinalizationConfirmButton`
- `LearningReportRevisionDialog`

Regel: Die Revisionsprojektion entsteht ausschliesslich aus `snapshot_json`, `LearningReportRevisionRecord` und dem gespeicherten SHA-256. Sie darf keine aktuelle Schueler-, Gruppen-, Kurs-, Kompetenz-, Beobachtungs- oder Diagrammquelle lesen. Das Draft-Ausgabemodell und die finale snapshotbasierte Adapterprojektion bleiben getrennte Quellen fuer denselben renderer-neutralen `ReportOutputModel`-Vertrag.

## Sprint 9A - Finaler PDF-Druck aus Berichtrevisionen

Registrierte Python-Module:

- `src/core/learning_report_pdf.py`
- `tests/test_learning_report_pdf.py`

Registrierte Klassen, Protokolle und Commands:

- `LearningReportPdfArtifactRecord`
- `LearningReportPdfArtifactRepository`
- `LearningReportPdfSnapshotValidator`
- `LearningReportPdfService`
- `LearningReportPdfError`
- `GenerateLearningReportPdfCommand`
- `LearningReportPdfApplicationService`
- `SQLiteLearningReportPdfArtifactRepository`
- `LearningReportPdfArtifactViewModel`

Registrierte Konstanten und Werte:

- `LEARNING_REPORT_PDF_ARTIFACT_ID_PREFIX` mit Wert `RPA`
- MIME-Type `application/pdf`

Registrierte Adapteroperationen:

- `StudentDesktopAdapter.generate_learning_report_pdf(learning_report_revision_id)`
- `StudentDesktopAdapter.load_learning_report_pdf_artifact(learning_report_revision_id)`

Registrierte Qt-Objektnamen:

- `LearningReportGenerateFinalPdfButton`
- `LearningReportFinalPdfStatus`

Regel: `RPA` identifiziert genau eine unveraenderliche PDF-Artefaktreferenz fuer eine `RPV`. Pro `learning_report_revision_id` existiert hoechstens eine `RPA`. `relative_file_path` ist relativ zum Verzeichnis der produktiven SQLite-Datei und bleibt innerhalb `documents/<student_id>/reports/<RPT>/<RPV>/`. `pdf_sha256` ist der kleingeschriebene SHA-256-Hexdigest der unveraenderten PDF-Bytes. `snapshot_sha256` kopiert den bei der Erzeugung erfolgreich bestaetigten Hash der Quellrevision. Es werden keine Renderer- oder Template-Versionsfelder eingefuehrt.

## UI Sprint 5 - Berichtswerkstatt und Revisionen

Registrierte Dialogmethoden und UI-State-Namen:

- `LearningReportDialog._set_workspace(key)`
- `LearningReportDialog._evidence_screen()`
- `LearningReportDialog._subject_evidence_editor(subject)`
- `LearningReportDialog._action_bar()`
- `LearningReportDialog._refresh_workspace_context()`
- `LearningReportDialog.workspace_navigation`
- `LearningReportDialog.evidence_navigation_group`
- `LearningReportDialog.evidence_stack`

Registrierte Qt-Objektnamen:

- `LearningReportWorkspaceNavigation`
- `LearningReportWorkspaceStack`
- `LearningReportActionBar`
- `LearningReportSaveButton`
- `LearningReportIncludeSubject_<subject_id>`
- `LearningReportSubjectText_<subject_id>_<text_key>`
- `LearningReportRevisionCanvas`
- `LearningReportRevisionPaper`

Regel: Diese Namen strukturieren ausschliesslich lokalen UI-State, Fokus, Bereichswechsel, zentrale Aktionshierarchie und Dokumentdarstellung. Sie fuehren keine Datenquelle, fachliche Filterung, Persistenz, Validierung, Snapshotauswertung oder Revisionslogik ein. `Schreiben` und `Kompetenzen & Belege` verwenden getrennte Widget-Stapel, lesen und schreiben jedoch weiterhin denselben bestehenden `LearningReportDraftViewModel` ueber die vorhandenen Dialogsignale.

## Sprint 7G.1 - Persistenter LEG-Arbeitsentwurf

Registrierte SQLite-Tabellen:

- `learning_conference_drafts`
- `learning_conference_draft_subjects`
- `learning_conference_draft_cross_topics`
- `learning_conference_draft_competencies`
- `learning_conference_draft_observations`
- `learning_conference_draft_charts`

Registrierte technische Felder und Werte:

- `learning_conference_draft_id`
- `conference_date`
- `responsible_teacher`
- `conversation_entry_text`
- `child_retrospective_text`
- `teacher_perspective_text`
- `strengths_text`
- `development_fields_text`
- `prepared_goals_text`
- `prepared_support_text`
- `prepared_agreements_text`
- `agreed_goals_text`
- `agreed_support_text`
- `agreed_agreements_text`
- `responsibilities_text`
- `next_review_date`
- `cross_topic_key`

Zulaessiger Status: `draft`.

Zulaessige `cross_topic_key`-Werte aus dem freigegebenen Prototyp:

- `work_habits`
- `social_behavior`
- `independence`
- `learning_organization`

Zulaessige Diagrammtypen:

- `documentation_coverage`
- `competency_timeline`
- `observation_timeline`

`learning_conference_draft_id` verwendet das Format `LCD-######`.

Registrierte Python-Module:

- `src/core/learning_conference_draft.py`
- `src/application/commands/learning_conference.py`
- `src/desktop_app/view_models/learning_conference_view_model.py`
- `tests/test_learning_conference_draft.py`

Registrierte Klassen und Application-Namen:

- `LearningConferenceDraftRecord`
- `LearningConferenceDraftRepository`
- `SQLiteLearningConferenceDraftRepository`
- `LearningConferenceDraftService`
- `LearningConferenceDraftApplicationService`
- `CreateLearningConferenceDraftCommand`
- `UpdateLearningConferenceDraftCommand`
- `GetLearningConferenceDraftQuery`
- `ListLearningConferenceDraftsQuery`
- `PrepareLearningConferenceQuery`
- `LearningConferenceApplicationService`
- `LearningConferenceDraftViewModel`
- `LearningConferencePreparationViewModel`
- `LearningConferenceCompetencyViewModel`
- `LearningConferenceEvidenceViewModel`
- `StudentDesktopAdapter.learning_conference_preparation_for_student(student_id)`
- `StudentDesktopAdapter.save_learning_conference_draft(draft)`
- `StudentDesktopAdapter.load_learning_conference_draft(learning_conference_draft_id)`
- `StudentDesktopAdapter.list_learning_conference_drafts_for_student(student_id)`

Registrierte Konstanten:

- `LEARNING_CONFERENCE_DRAFT_ID_PREFIX`
- `LEARNING_CONFERENCE_DRAFT_STATUS`
- `LEARNING_CONFERENCE_CROSS_TOPIC_KEYS`
- `LEARNING_CONFERENCE_CHART_TYPES`

Regel: Der LEG-Arbeitsentwurf ist keine Berichtsentitaet und kein `report_type`. Er speichert manuelle Inhalte und reine Referenzen, aber weder Kompetenztexte noch Beobachtungsfachdaten, Kompetenzstaende oder Diagrammdaten.

## Sprint 7G.2 - Produktiver LEG-Arbeitsbereich

Registrierte Python-Module und UI-Einstiege:

- `src/desktop_app/dialogs/learning_conference_dialog.py`
- `tests/test_learning_conference_ui.py`
- `LearningConferenceDialog`
- `LearningConferenceDialog.save_requested`
- `LearningConferenceDialog.draft_view_model()`
- `LearningConferenceDialog.apply_saved_draft(draft)`
- `StudentProfileScreen.learning_conference_requested`
- `AppShell.open_learning_conference_dialog(student_id)`
- `_documentation_state_label(value)`
- `_rating_label(value)`

Registrierte zentrale Objektrollen:

- `LearningConferenceProfileAction`
- `LearningConferenceWorkspace`
- `LearningConferencePreparationPanel`
- `LearningConferenceConversationPanel`
- `LearningConferenceCard`
- `LearningConferenceSoftBlock`
- `LearningConferenceChartCard`
- `LearningConferenceHero`
- `LearningConferenceSection`
- `LearningConferencePrepared`
- `LearningConferenceShared`
- `LearningConferenceWarning`
- `LearningConferenceSaveButton`
- `LearningConferenceCanonicalStatus`
- `LearningConferenceUnavailableEvidence`

Regel: Diese Namen portieren ausschliesslich die freigegebene UX und binden sie an den bestehenden 7G.1-Draft. Sie fuehren keine neue Datenquelle, kein technisches Fachfeld und keine zweite Kompetenz- oder Beobachtungsprojektion ein.

## Sprint 7G.3 - Dokumentationsfilter der LEG-Kompetenzauswahl

Registrierte fluechtige ViewModel-Felder und Funktionen:

- `LearningConferenceCompetencyViewModel.observation_dates`
- `LearningConferenceCompetencyViewModel.has_current_confirmation`
- `LearningConferenceCompetencyViewModel.is_documented_in_period(period_start, period_end)`
- `_parse_evidence_date(value)`

Registrierte Leseparameter und UI-Rollen:

- `retained_competency_ids`
- `LearningConferenceCompetencyFilterNote`
- `LearningConferenceCompetencyEmpty_<subject_id>`
- `LearningConferenceDialog._update_competency_visibility(selected_subjects)`
- `LearningConferenceDialog._competency_filter_period()`
- `LearningConferenceDialog._optional_date_edit(value, accessible_name)`
- `LearningConferenceDialog._optional_date_value(edit)`

Regel: `observation_dates` enthaelt ausschliesslich Datumsreferenzen bereits kanonisch beruecksichtigter aktiver Kompetenzbeobachtungen des Kindes. `has_current_confirmation` bildet nur das Vorhandensein der bestehenden aktuellen Bestaetigung ab. Beide Werte steuern ausschliesslich die sichtbare LEG-Auswahl und berechnen keinen Kompetenzstatus. `retained_competency_ids` darf historische Draft-Referenzen in derselben kanonischen Projektion aufloesbar halten, veraendert aber deren Statuslogik und die Standardprojektion ohne diesen Parameter nicht.

## UI Sprint 6B - Phasenorientierter LEG-Workspace

Registrierte lokale UI-Kompositionen:

- `LearningConferencePhaseNavigation`
- `LearningConferencePhaseButton_<phase_key>`
- `LearningConferencePhaseWorkspace`
- `LearningConferencePhaseScroll`
- `LearningConferenceEvidenceSummary`
- `LearningConferenceActionBar`
- `LearningConferenceDirtyBadge`
- `LearningConferenceValidationMessage`
- `LearningConferenceCloseDialog`
- `LearningConferenceDraftSelectionDialog`
- `LearningConferenceDraftChoice_<learning_conference_draft_id>`

Registrierte reine Leseprojektionserweiterung:

- `LearningConferencePreparationViewModel.course_name`

Registrierte fluechtige UI-Schluessel:

- `goal`
- `strengths`
- `development`
- `goals`
- `evidence`
- `agreements`

Regel: Die sechs Schluessel strukturieren ausschliesslich den lokalen aktiven Phasen-, Fokus-, Scroll- und Dirty-State des bestehenden `LearningConferenceDialog`. `LearningConferencePhaseNavigation` und `LearningConferenceDraftSelectionDialog` sind lokale Qt-Kompositionen aus registrierten Basiskomponenten. Bei mindestens einem vorhandenen LEG wählt die Auswahl bewusst einen gespeicherten LCD oder ein neues, noch ungespeichertes eigenständiges Gespräch. Sie fuehren keine Datenquelle, fachliche Phase, Abschlusslogik, Persistenz, Repository-Verantwortung oder neue Feldbedeutung ein. `LearningConferencePreparationViewModel.course_name` reicht nur den bereits vorhandenen Kursnamen aus der Schuelerprojektion in den Kontextkopf weiter. `agreed_goals_text` bleibt unveraendert persistiert und wird nur sichtbar der Phase `goals` zugeordnet.

## Sprint 8A - Produktiver Stundenplan

Registrierte technische Felder und Werte:

- `timetable_entry_id`
- `weekday`
- `start_time`
- `end_time`
- `target_type`
- `target_id`
- `room`
- `deleted_at`
- `group`
- `course`
- `course_group`

Registrierte Python-Komponenten:

- `src/core/timetable.py`
- `src/application/commands/timetable.py`
- `src/desktop_app/adapters/timetable_desktop_adapter.py`
- `src/desktop_app/view_models/timetable_view_model.py`
- `src/desktop_app/dialogs/timetable_entry_dialog.py`
- `TimetableEntry`
- `TimetableOccurrence`
- `TimetableService`
- `TimetableValidator`
- `TimetableValidationError`
- `TimetableProjection`
- `TimetableRepository`
- `SQLiteTimetableRepository`
- `SaveTimetableEntryCommand`
- `TimetableApplicationService`
- `TimetableDesktopAdapter`
- `TimetableOptionViewModel`
- `TimetableEntryViewModel`
- `TimetableDayViewModel`
- `TimetableWeekViewModel`
- `TimetableOccurrenceViewModel`
- `TimetableReadProjectionViewModel`
- `TimetableEntryDialog`
- `build_timetable_projection(entries, at)`

Registrierte Adapter-, Repository- und UI-Einstiege:

- `SQLiteTimetableRepository.list_entries()`
- `SQLiteTimetableRepository.get_entry(timetable_entry_id)`
- `SQLiteTimetableRepository.create_entry(entry)`
- `SQLiteTimetableRepository.update_entry(entry)`
- `SQLiteTimetableRepository.next_timetable_entry_id()`
- `SQLiteTimetableRepository.next_sort_order(weekday)`
- `TimetableDesktopAdapter.week_view_model()`
- `TimetableDesktopAdapter.save_entry(command)`
- `TimetableDesktopAdapter.set_entry_active(timetable_entry_id, active)`
- `TimetableDesktopAdapter.delete_entry(timetable_entry_id)`
- `TimetableDesktopAdapter.read_projection(at)`
- `SettingsScreen.timetable_add_requested`
- `SettingsScreen.timetable_edit_requested`
- `SettingsScreen.timetable_delete_requested`
- `SettingsScreen.timetable_active_requested`
- `TimetableSettingsSection`
- `TimetableEmptyState`
- `TimetableDay_{weekday}`
- `TimetableEntry_{timetable_entry_id}`
- `TimetableAdd_{weekday}`
- `TimetableActive_{timetable_entry_id}`

Regel: `weekday` verwendet ISO-Wochentage 1 bis 5. Zeiten werden kanonisch als `HH:MM` gespeichert. `target_type` ist genau `group`, `course` oder `course_group`; `target_id` referenziert die dazu passende bestehende Stammdaten-ID. Die Projektion erhaelt den Auswertungszeitpunkt explizit und verwendet kein verborgenes `datetime.now()`.

## Sprint 8B - Stundenplanbasiertes Dashboard

Registrierte Python-Komponenten und ViewModels:

- `DashboardDocumentationCellViewModel`
- `DashboardDocumentationGroupViewModel`
- `DashboardDocumentationHeatmapViewModel`
- `DashboardLessonCard`
- `StudentDesktopAdapter.dashboard_documentation_heatmap()`
- `StudentDesktopAdapter.list_students(..., course_ids)`
- `OverviewScreen.set_dashboard(projection, heatmap, at, has_timetable_entries)`
- `OverviewScreen.timetable_target_selected`
- `OverviewScreen.timetable_observation_requested`
- `OverviewScreen.settings_timetable_requested`
- `AppShell.refresh_dashboard(at)`
- `AppShell.show_students_for_timetable_target(target_type, target_id)`
- `AppShell.prepare_timetable_observation(subject_id, subject_label, target_type, target_id, target_label)`
- `NewObservationDialog.prefill_subject_id`
- `NewObservationDialog.prefill_context`
- `AppShell.now_provider`
- `AppShell.dashboard_refresh_timer`

Registrierter temporaerer UI-State:

- `pending_observation_subject_id`
- `pending_observation_subject_label`
- `pending_observation_target_label`

Regel: Das Dashboard liest ausschliesslich kanonische Stundenplan-, Stammdaten- und Dokumentationsprojektionen. Der aktuelle Zeitpunkt wird am Shell-Rand explizit an `TimetableDesktopAdapter.read_projection(at)` und den Screen weitergereicht. Die Stundenplanaktion merkt Fach und sichtbaren Unterrichtskontext nur fluechtig bis zur Kindauswahl vor; sie erzeugt keine neue Beobachtungs- oder Stundenplandatenquelle.

## Sprint 8B.1 - Dashboard UX-Referenz

Registrierte UI-Komponenten und Navigation:

- `dashboard`
- `GroupOverviewScreen`
- `DashboardHeroIllustrationSpace`
- `DashboardHeroVisualTimeline`
- `DASHBOARD_SUBJECT_VIGNETTE_ASSETS`
- `DASHBOARD_SUBJECT_VIGNETTE_MIN_WIDTH`
- `DASHBOARD_SUBJECT_VIGNETTE_COMPACT_WIDTH`
- `DASHBOARD_SUBJECT_VIGNETTE_SIZE`
- `DASHBOARD_SUBJECT_VIGNETTE_COMPACT_SIZE`
- `DASHBOARD_SUBJECT_VIGNETTE_OVERLAP`
- `OverviewScreen._subject_vignette(subject_id)`
- `OverviewScreen._update_hero_vignette_visibility()`
- `DashboardHeroSubjectVignette`
- `DashboardHeroSubjectImage`
- `subjectId`
- `DashboardTimeline`
- `DashboardHeatmapMatrix`
- `DashboardMatchingChildren`

Registrierte produktive Fachmotive:

- `assets/subject_vignettes/deutsch.png`
- `assets/subject_vignettes/mathematik.png`
- `assets/subject_vignettes/epu.png`
- `assets/subject_vignettes/musik.png`
- `assets/subject_vignettes/kunst.png`
- `assets/subject_vignettes/sport.png`
- `assets/subject_vignettes/ethik.png`
- `assets/subject_vignettes/religion.png`
- `assets/subject_vignettes/werken.png`
- `assets/subject_vignettes/schulgarten.png`

Regel: `dashboard` ist ein eigener Hauptnavigationspunkt. Der bestehende technische Navigationsschluessel `overview` und seine Stammgruppen-/Kursverbunduebersicht bleiben getrennt erhalten. Sprint 8B.1 veraendert ausschliesslich Screen-Komposition, Groessenverhaeltnisse, Weissraum und Theme-Stile; Stundenplan-, Dokumentations-, Ziel- und Beobachtungsprojektionen bleiben unveraendert. Die `DashboardHeroSubject*`-Namen und `DASHBOARD_SUBJECT_VIGNETTE_ASSETS` bezeichnen ausschliesslich dekorative, nicht interaktive Fachmotive fuer die zehn tatsaechlichen Unterrichtsfaecher innerhalb der vorhandenen Stundenansicht. Die Zuordnung erfolgt nur ueber stabile kanonische Fach-IDs; `Sozialkompetenz`, unbekannte Fach-IDs und fehlende Dateien blenden das Motiv ohne Ersatztext oder Layoutluecke aus. Die Motive bleiben ohne Fokus und eigene Accessibility-Ausgabe, verwenden die vorhandene mindestens zweifache Quellaufloesung fuer HiDPI, werden im kompakten Dashboardbereich proportional verkleinert und darunter ausgeblendet. Sie begruenden keine allgemeine Asset-Architektur oder neue Fachlogik.

## Sprint 8B.2 - Dashboard ohne allgemeine Uebersichtsbereiche

Regel: Der Dashboard-Screen endet nach `DashboardMatchingChildren`. Allgemeine Stammgruppen-, Kursverbund- und sonstige Schnellzugriffskarten gehoeren ausschliesslich zu `GroupOverviewScreen` unter dem getrennten Navigationspunkt `overview`. Das Dashboard besitzt dafuer keine Layouts, Signale oder Stammdatenbefuellung.

## Sprint 8B.3 - Passende Kinder als Dokumentationshilfe

Registrierte Projektion und UI-Einstiege:

- `DashboardSuggestedStudentViewModel`
- `StudentDesktopAdapter.list_dashboard_suggested_students(target_type, target_id, subject_id, subject_label, at, limit)`
- `OverviewScreen.timetable_student_observation_requested`
- `AppShell.open_dashboard_observation(student_id, subject_id, subject_label, target_label)`
- `DashboardMatchingChildRow`

Regel: Die Projektion verwendet ausschliesslich aktive Zielmitglieder und aktive Beobachtungen mit eindeutigem Bezug zum Stundenfach. Sie erhaelt `at` explizit, begrenzt auf hoechstens fuenf Kinder und sortiert ohne Ratings, Kompetenzstatus oder Scores: keine Fachbeobachtung zuerst, danach letzte Fachbeobachtung aufsteigend, heutige Fachbeobachtung zuletzt und bei Gleichstand sichtbarer Name alphabetisch plus stabile `student_id`.

## UI Sprint 1 - Product Shell und Interaction Foundations

Registrierte Dateien und Assets:

- `src/desktop_app/components.py`
- `src/desktop_app/icons.py`
- `src/desktop_app/screens/students_workspace.py`
- `assets/icons/today.svg`
- `assets/icons/students.svg`
- `assets/icons/master-data.svg`
- `assets/icons/settings.svg`
- `assets/icons/info.svg`
- `assets/icons/search.svg`
- `assets/icons/close.svg`
- `assets/icons/chevron-down.svg`

Registrierte Komponenten und Helfer (Component Library V1 und V2):

- `AppCard`
- `AppCard.set_selected(selected)`
- `AppCard.set_pressed(pressed)`
- `SectionHeader`
- `SectionHeader.add_action(action)`
- `FilterBar`
- `FilterBar.reset_requested`
- `FilterBar.set_context_filter(label, active)`
- `FilterBar.add_filter_widget(widget)`
- `FilterChip`
- `FilterChip.remove_requested`
- `FilterChip.set_label(label)`
- `IconButton`
- `PageHeader`
- `SegmentedControl`
- `SegmentedControl.selection_changed`
- `SearchField`
- `SearchField.find_shortcut`
- `StatusBadge`
- `StatusBadge.setText(text)`
- `StatusBadge.ratingToken`
- `RatingBadgeButton`
- `RatingBadgeButton.set_compact(compact)`
- `apply_rating_badge_variant(widget, rating_token)`
- `InlineMessage`
- `EmptyState`
- `EmptyState._update_accessibility()`
- `Toast`
- `Toast.show_message(text, tone, duration_ms)`
- `configure_button(button, role, accessible_name)`
- `set_button_role(button, role)`
- `StudentsWorkspace`
- `StudentsWorkspace.courses_screen`
- `StudentsWorkspace.new_student_requested`
- `StudentsWorkspace.all_students_requested`
- `StudentsWorkspace.course_selected`
- `StudentsWorkspace.set_master_data(view_model, group_summaries)`
- `StudentsWorkspace.show_section(key)`
- `StudentsWorkspace.show_student_list(source_key)`
- `StudentsWorkspace.show_source_selection()`
- `StudentsWorkspace.list_source_key()`
- `StudentsWorkspace.current_content_key()`
- `STUDENT_WORKSPACE_SEGMENTS`
- `AppShell.show_all_students()`
- `AppShell.show_students_for_course(course_id)`
- `GroupOverviewScreen.direct_course_selected`
- `ICON_NAMES`
- `ICON_SIZE_SMALL`
- `ICON_SIZE_MEDIUM`
- `ICON_SIZE_LARGE`
- `icon_path(name)`
- `load_icon(name)`

Registrierte Theme-Tokens:

- `SPACING_4`, `SPACING_8`, `SPACING_12`, `SPACING_16`, `SPACING_24`, `SPACING_32`, `SPACING_48`
- `RADIUS_SMALL`, `RADIUS_MEDIUM`, `RADIUS_LARGE`, `RADIUS_XLARGE`
- `ELEVATION_FLAT`, `ELEVATION_CARD`, `ELEVATION_OVERLAY`
- `MOTION_FAST_MS`, `MOTION_STANDARD_MS`, `MOTION_SLOW_MS`
- `TYPOGRAPHY_STYLES`
- `COLOR_SUCCESS`, `COLOR_WARNING`, `COLOR_INFO`, `COLOR_FOCUS`

Erweiterte Felder von `NavigationItem`:

- `section`
- `icon_name`

Regel: Der sichtbare Navigationsname des bestehenden technischen Schluessels `dashboard` lautet `Heute`. Globale produktive Ziele sind ausschliesslich `dashboard`, `students`, `master_data` und `settings`, gruppiert in `ARBEIT` und `VERWALTUNG`. Der fruehere Schluessel `overview` wird nicht mehr global aufgeloest; `GroupOverviewScreen` bleibt als bestehende reine Projektion innerhalb von `StudentsWorkspace` erhalten. `PlaceholderScreen` bleibt als registriertes Modul historisch verfuegbar, ist aber kein Product-Shell-Ziel.

Regel: `StudentsWorkspace` komponiert die lokalen Segmente `groups`, `courses`, `course_groups` und `all` nur aus vorhandenen Adapter-/ViewModel-Projektionen und lokalem UI-State. Es fuehrt weder eine Datenquelle noch Businesslogik, SQLite-Zugriff, Persistenz oder einen Schreibprozess ein. Die direkte Kursansicht uebergibt eine vorhandene `course_id` an `StudentDesktopAdapter.list_students(course_id=...)`. Beobachtungs-, Kompetenz-, Berichts- und LEG-Pfade bleiben ueber das bestehende Schuelerprofil erreichbar.

## Premium UI Sprint 2 - Dialog Experience und Workspace Polish

Registrierte UI-Komponenten und Objektrollen:

- `DialogHeader`
- `DialogHeader.add_action(action)`
- `DialogActionBar`
- `ObservationDialogZone.zoneRole`
- `zoneRole = context`
- `zoneRole = primary`
- `zoneRole = entry`
- `LearningReportDialog.reject()`

Registrierte Dialogicons:

- `assets/icons/student-record.svg`
- `assets/icons/master-data-dialog.svg`
- `assets/icons/timetable-dialog.svg`
- `assets/icons/observation.svg`
- `assets/icons/report.svg`
- `assets/icons/conference.svg`

Regel: `DialogHeader`, `DialogActionBar` und `zoneRole` strukturieren ausschliesslich visuelle Hierarchie, Kontext, Fokusreihenfolge und lokale Surface-Gewichtung vorhandener Dialoge. `LearningReportDialog.reject()` bestaetigt nur das Verwerfen eines bereits lokal erkannten Dirty-State. Diese Namen besitzen keine Datenquelle, erzeugen keine Fachlogik und veraendern weder Adapter-, ViewModel-, Repository-, SQLite-, Navigations- noch Speicherpfade.

## UI Sprint 3 - Motion System und Microinteractions

Registrierte Datei:

- `src/desktop_app/motion.py`

Registrierte Motion-Namen:

- `MotionPolicy`
- `motion_policy`
- `set_reduced_motion(enabled)`
- `reduced_motion_enabled()`
- `motion_duration(duration_ms)`
- `animate_value(owner, key, start_value, end_value, update, duration_ms, easing)`
- `animate_opacity(widget, visible, duration_ms, key)`
- `animate_feedback(widget, key, duration_ms)`
- `animate_selection(widget, key)`
- `animate_save_confirmation(button)`
- `MotionDialog`
- `install_button_motion(button)`
- `install_card_motion(card)`
- `install_item_selection_motion(list_widget)`
- `stop_motion(owner, key)`

Regel: Motion ist ausschliesslich lokaler, fluechtiger UI-State. Animationen setzen keine fachlichen Zustaende, besitzen keine Datenquelle und duerfen Signale, Navigation, Filter oder Schreibprozesse nicht verzoegern. Pro Widget und semantischem Schluessel existiert hoechstens eine laufende Animation; Reduced Motion setzt denselben Endzustand ohne Bewegung.

## UI Sprint 4 - Schuelerprofil und Beobachtungs-Workspace

Registrierte Profilnamen:

- `StudentProfilePageHeader`
- `StudentProfileHeaderSurface`
- `StudentProfilePrimaryAction`
- `StudentProfileMoreActions`
- `StudentProfileNavigation`
- `StudentProfileTabs`
- `DocumentationRing`
- `StudentProfileAvatar`
- `StudentProfileContextBadge`
- `StudentProfileHeaderDocumentation`
- `StudentProfileDocumentationRing`
- `StudentProfileOverviewCards`
- `StudentProfileOrientationCard`
- `StudentProfileOrientationChange`
- `StudentProfileOrientationStatusChange`
- `StudentProfileOrientationEvidence`
- `StudentProfileDevelopmentArrow`
- `StudentProfileEvidenceBadge`
- `StudentProfileHistoricalBadge`
- `StudentProfileCompetencySummaryCard`
- `StudentProfileUndocumentedCard`
- `StudentProfileEyebrow`
- `StudentProfileDocumentationMetric`
- `StudentProfileDashboardSummaryRow`
- `StudentProfileOpenCompetencyCockpit`
- `StudentProfileOpenUndocumented`
- `CompetencyCockpitSearch`
- `CompetencyCockpitStageFilter`
- `StudentProfileScreen._select_profile_section(key)`
- `StudentProfileScreen._sync_profile_navigation(index)`
- `StudentProfileScreen._update_profile_header_context()`
- `StudentProfileScreen._apply_overview_card_layout(compact)`
- `StudentProfileScreen._orientation_change_row(change)`
- `StudentProfileScreen._orientation_status_row(label, rating, status_label)`
- `StudentProfileScreen._orientation_evidence_excerpt(event)`
- `StudentProfileScreen._open_undocumented_competencies()`
- `StudentProfileScreen._matches_competency_learning_stage(competency, learning_stage_filter)`
- `StudentProfileScreen._matches_competency_search(competency, learning_area, topic, search_text)`

Registrierte Dialognamen:

- `OBSERVATION_STAGE_FILTERS`
- `ObservationDialogPageHeader`
- `ObservationLearningStageFilter`
- `ObservationValidationMessage`
- `ObservationFileRow`
- `NewObservationDialog._catalog_stage_filter_key`
- `NewObservationDialog._change_catalog_stage_filter(filter_key)`
- `NewObservationDialog._matches_catalog_learning_stage(competency)`

Regel: Beide Klassenstufenfilter lesen ausschliesslich das bestehende Katalogfeld `learning_stage`. `matching` zeigt `stage_1_3` und `cross_stage`, `stage_4` zeigt `stage_4` und `cross_stage`, `all` zeigt alle aktiven aktuellen Katalogzeilen. Filterung bleibt lokaler UI-State und erzeugt keine neue Datenquelle, Berechnung oder Persistenz. Initial ausgewaehlte Edit-Kompetenzen bleiben unabhaengig vom Filter sichtbar und geoeffnet; historische beziehungsweise inaktive Kompetenzen werden nie als neue Auswahl reaktiviert.

## LEG-Abschluss und Revision

Registrierte Domainnamen:

- `LearningConferenceRecord` (`LCF`)
- `LearningConferenceRevisionRecord` (`LCV`)
- `LearningConferenceCompletionSource`
- `LearningConferenceCompletionResult`
- `LearningConferenceCompletionError`
- `LearningConferenceSnapshotBuilder`
- `LearningConferenceCompletionService`
- `LearningConferenceRevisionReadService`

Registrierte Application- und Persistenznamen:

- `LearningConferenceCompletionApplicationService`
- `LearningConferenceRevisionApplicationService`
- `SQLiteLearningConferenceRepository`
- `learning_conferences`
- `learning_conference_revisions`

Registrierte UI-/Projektionsnamen:

- `LearningConferenceRevisionStatusViewModel`
- `LearningConferenceRevisionListItemViewModel`
- `LearningConferenceRevisionViewModel`
- `LearningConferenceCompletionErrorViewModel`
- `LearningConferenceRevisionDialog`

Registrierte IDs und Statuswerte:

- `learning_conference_id` mit Praefix `LCF-`
- `learning_conference_revision_id` mit Praefix `LCV-`
- LCV-Status `completed`
- LCV-Status `superseded`
- `snapshot_schema_version`
- `snapshot_json`
- `snapshot_sha256`

Begriffsregel:

- `Abschluss` ist der explizite, validierte und atomare Schreibbefehl vom LCD zum LCF/LCV.
- `Revision` bezeichnet ausschliesslich eine unveraenderliche LCV; der LCD bleibt ein Draft.
- `Snapshotvertrag` bezeichnet die LEG-spezifische kanonische JSON-Struktur und ist keine gemeinsame Bericht-/LEG-Domain.

## Sprint 10B - Finales LEG-PDF aus abgeschlossener Revision

Registrierte Python-Module:

- `src/core/learning_conference_pdf.py`
- `tests/test_learning_conference_pdf.py`

Registrierte Klassen, Protokolle und Commands:

- `LearningConferencePdfArtifactRecord`
- `LearningConferencePdfArtifactRepository`
- `LearningConferencePdfSnapshotValidator`
- `LearningConferencePdfOutputModelBuilder`
- `LearningConferencePdfService`
- `LearningConferencePdfError`
- `GenerateLearningConferencePdfCommand`
- `LearningConferencePdfApplicationService`
- `SQLiteLearningConferencePdfArtifactRepository`
- `LearningConferencePdfArtifactViewModel`

Registrierte Konstanten und Werte:

- `LEARNING_CONFERENCE_PDF_ARTIFACT_ID_PREFIX` mit Wert `LCA`
- MIME-Type `application/pdf`

Registrierte technische Felder und Adapteroperationen:

- `learning_conference_pdf_artifact_id`
- `relative_file_path`
- `mime_type`
- `file_size_bytes`
- `pdf_sha256`
- `StudentDesktopAdapter.generate_learning_conference_pdf(learning_conference_revision_id)`
- `StudentDesktopAdapter.load_learning_conference_pdf_artifact(learning_conference_revision_id)`

Registrierte Qt-Objektnamen:

- `LearningConferenceGenerateFinalPdfButton`
- `LearningConferenceFinalPdfStatus`

Regel: `LCA` identifiziert genau eine unveraenderliche PDF-Artefaktreferenz fuer eine `LCV`. Pro `learning_conference_revision_id` existiert hoechstens eine `LCA`. Neue Erzeugung ist nur fuer Status `completed` erlaubt. `relative_file_path` liegt relativ zur produktiven SQLite-Datei innerhalb `documents/<student_id>/learning_conferences/<LCF>/<LCV>/`; der Dateiname enthaelt keinen Schuelerklartext. `pdf_sha256` ist der kleingeschriebene SHA-256-Hexdigest der PDF-Bytes. Die renderer-neutrale PDF-Projektion ist keine Berichtsdomain und liest ausschliesslich den verifizierten LCV-Snapshot.

## Brand Color Harmonization - Theme- und Dialogrollen

Registrierte zentrale Marken-Tokens:

- `BRAND_NAVY`
- `BRAND_BLUE`
- `BRAND_BLUE_HOVER`
- `BRAND_BLUE_PRESSED`
- `BRAND_TEAL`
- `BRAND_GREEN`
- `BRAND_LIME`
- `BRAND_ORANGE`
- `LIGHT_BLUE`
- `LIGHT_TEAL`
- `LIGHT_GREEN`
- `LIGHT_LIME`
- `LIGHT_ORANGE`
- `LIGHT_NEUTRAL`

Registrierte zentrale Dialog-Kontextnamen:

- `DialogHeader.CONTEXT_ROLES`
- `DialogHeader.context_role`
- `dialogContext`
- `dialogContext = neutral`
- `dialogContext = observation`
- `dialogContext = report`
- `dialogContext = learning_conference`
- `dialogContextSurface`

Regel: `dialogContext` und `dialogContextSurface` sind ausschliesslich
visuelle, nicht persistente Qt-Properties. Sie unterscheiden geoeffnete
Arbeitsbereiche und duerfen keine Status-, Bewertungs-, Leistungs-, Prioritaets-,
Erfolgs- oder Fehlerbedeutung erhalten. Sie besitzen keine Datenquelle und
veraendern weder Kursfarben, Bewertungsbadges, Dokumentationsabdeckung,
Feedbackfarben noch Adapter-, ViewModel-, Repository-, SQLite-, Navigations-
oder Speicherpfade. Unbekannte `DialogHeader.context_role`-Werte werden
abgelehnt; kleine und administrative Dialoge verwenden den Default `neutral`.
## Performance-P1 - gebündelte Dokumentationsprojektion

| Technischer Name | Bedeutung | Eigentümer |
|---|---|---|
| `StudentDocumentationProjectionBatch` | Unveränderlicher, refresh-lokaler Read-Batch aus aktiven Schülern, Gruppen, Kursen, Katalog, Fachauswahl, aktiven Beobachtungen samt Kompetenz-Snapshots, Dokumentmetadaten, Bestätigungen und technischer Frische; keine neue Datenquelle und kein globaler Cache | Core Persistence / Desktop Adapter |
| `SQLiteStudentDocumentationProjectionRepository` | Eng zugeschnittener transaktionskonsistenter SQLite-Read für Schülerliste und Dokumentations-Heatmap; lädt jede benötigte Tabelle höchstens einmal je Refresh und führt weder DDL noch Schemainitialisierung aus | Core Persistence |
| `project_competency_freshness` | Gemeinsame Qt-freie Faltung bereits geladener Persistenzereignisse in denselben kanonischen Bestätigungsfrischezustand wie der schülerbezogene Einzelread | Core Persistence |
| `StudentDesktopAdapter.dashboard_documentation_refresh` | Adapterprojektion, die Heatmap und stundenbezogene Kindvorschläge aus genau demselben refresh-lokalen Batch erzeugt | Desktop Adapter |
| `StudentProfileProjectionBundle` | Unveränderliche, nur für genau eine Profilnavigation lebende Komposition der bestehenden Profilprojektionen aus einem gemeinsamen Read-Snapshot; kein globaler oder dauerhafter Cache | Desktop ViewModel / Adapter |
| `StudentDesktopAdapter.student_profile_projection_bundle` | Adaptergrenze, die Profilkopf, Beobachtungen samt Ratings und Belegen, Kompetenzübersicht, Dokumentationsstatus, Dokumente, Cockpit und Profil-Dashboard aus genau einem frischen Batch zusammensetzt | Desktop Adapter |

Diese Namen ändern weder Datenmodell noch Statusregeln. Der Batch lebt nur für
einen Adapteraufruf. Schülerprofil, Schülerliste und Dashboard dürfen ihn
jeweils request-lokal als gemeinsame Projektionsbasis verwenden; Bericht und
LEG behalten ihre getrennten zeitraumbezogenen Reads.
