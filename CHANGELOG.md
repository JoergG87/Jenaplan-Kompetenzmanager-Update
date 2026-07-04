# CHANGELOG

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
