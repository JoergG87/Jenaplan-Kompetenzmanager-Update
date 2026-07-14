# CHANGELOG

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
