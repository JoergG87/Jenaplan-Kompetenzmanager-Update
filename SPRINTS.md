# Sprintplanung

SPRINTS.md dient ausschließlich der operativen Projektplanung.

ROADMAP.md beschreibt die langfristige Vision. SPRINTS.md ersetzt ROADMAP.md nicht.

## Sprintübersicht

## Pilot 0.1.1 - Releasevorbereitung ✅

- [x] Aktuellen committed UI-Fix und sauberen Quellstand geprüft
- [x] Produktiven Beobachtungsdialog mit fiktiven Pilotdaten und vollständiger farbiger Bewertungszeile neu aufgenommen
- [x] Handbucherklärung auf Text, Symbol, Auswahlzustand und ergänzende Farborientierung ausgerichtet
- [x] Pilotversion, Installationsquellen und Paketnamen auf `0.1.1` vorbereitet
- [x] Schnellstart, Erste Schritte und Backup-Anleitung in den reproduzierbaren Dokumentbau aufgenommen
- [x] Laura-Paketbau auf ausschließlich frisch erzeugte Release-Ausgaben ausgerichtet
- [x] Keine weitere Produkt-UI, Fachlogik, Datenmodell- oder Testdatenänderung

## Sprint 8D - Laura-Pilotpaket ✅

- [x] Selbsterklärendes Laura-ZIP mit nummerierter Übergabestruktur erstellt
- [x] Startdatei und Pilotversionsübersicht mit ausschließlich fiktiven Testdaten ergänzt
- [x] DMG, Installation, Erste Schritte, Benutzerhandbuch, Schnellstart, Pilottest-Excel und Backup vollständig gebündelt
- [x] ZIP entpackt und auf Struktur, verständliche Dateinamen, fehlende Entwicklerdateien und fehlende ZIP-in-ZIP-Struktur geprüft
- [x] Alle PDFs geprüft, Excel-Datei in Microsoft Excel geöffnet und Backup-Skript validiert
- [x] Laura-DMG-Prüfsumme und fiktiver Datenmodus mit 24 Kindern erneut bestätigt
- [x] Keine Fachlogik, App-UI, Datenmodelle, Migrationen, neuen Produktfunktionen, Staging oder Commit

## Sprint 8C - Pilotpaket UX und Installation ✅

- [x] Gebrandetes, ruhiges DMG-Layout mit App, Programme-Verknüpfung und Installationsanleitung umgesetzt
- [x] Lehrkraft-Installationsanleitung und reproduzierbares PDF mit eindeutigem Versionsnamen erstellt
- [x] Benutzerhandbuch um Installation und ersten Start ergänzt und als gestaltetes PDF mit Inhaltsverzeichnis, Seitenzahlen und aktuellen Screenshots geprüft
- [x] Technischen leeren Smoke-Test und Laura-Pilot mit 24 ausschließlich fiktiven Kindern klar getrennt
- [x] Laura-Pilot um Gruppen, Kurse, Stundenplan, Beobachtungen, Bericht-/LEG-Drafts, Revisionen und finale Beispiel-PDFs vervollständigt
- [x] Update-durch-App-Austausch, getrennte lokale Daten und technisches Backup verifiziert
- [x] Keine Fachlogik, App-UI, Datenmodelle, Migrationen, neue Funktionen, Staging oder Commit

## Pilot-Deployment macOS 0.1.0

- [x] Aktuellen Entry Point, Abhängigkeiten, Ressourcen, PDF-Renderer, Pfade, Imports und Qt-Plug-ins geprüft
- [x] PyInstaller 6.21 als Python-3.14-fähigen, kontrollierbaren Packaging-Weg festgelegt
- [x] Apple-Silicon-App-Bundle mit stabiler Bundle-ID, Icon, Pilotversion und macOS-13-Mindestversion vorbereitet
- [x] Produktive Benutzerdaten vollständig aus der `.app` nach `~/Library/Application Support/Jenaplan-Kompetenzmanager/` getrennt
- [x] Leere Smoke-Test-Variante und ausdrücklich fiktive Laura-Buildoption ohne Entwicklerdatenbank umgesetzt
- [x] Drag-and-drop-DMG, technische Installation, Gatekeeper-Hinweis und Update-durch-App-Austausch vorbereitet
- [x] Sicheres geschlossenes App-Backup für SQLite und verwaltete Dokumente ergänzt
- [x] Automatisierten Packaged-App-Smoke-Test ergänzt
- [ ] Developer-ID-Signierung und Apple-Notarisierung; lokal ist keine geeignete Identität verfügbar
- [ ] Vollständiger manueller Abnahmelauf auf zweitem macOS-Benutzerkonto oder repositoryfreiem Zweitgerät
- [x] Kein Windows-Paket, Auto-Updater, App-Store-Release, Produktcode-Redesign, Staging oder Commit

## Sprint 11A - Release Documentation Alignment ✅

- [x] `PROJECT.md` auf den produktiven PySide-/SQLite-Systemstand nach Sprint 10B und den Schuelerprofil-UX-Fixes ausgerichtet
- [x] Abgeschlossene produktive Sprints konsistent als abgeschlossen markiert
- [x] Historische Excel-/Workbook-Sprints ohne Inhaltsverlust als beendet beziehungsweise abgeloest gekennzeichnet
- [x] Alte Commit-Statushinweise aus den historischen Sprintbloecken entfernt
- [x] ADR-050 bis ADR-057 um einheitliche Umsetzungs- und Offenheitsstatus ergaenzt
- [x] Verbleibende Product-Owner- und Betriebsentscheidungen sichtbar erhalten
- [x] Changelog ohne Release-Version oder Auslieferungsaussage vorbereitet
- [x] Keine Produktfunktion, Architektur, Tests, Datenmodell-, Prototyp- oder Pilottestdatei geaendert

## Sprint 10B - LEG-PDF aus unveraenderlicher Revision ✅

- [x] PDF-Erzeugung ausschliesslich fuer eine aktuelle `completed`-Revision (`LCV`) festgelegt
- [x] LEG-Snapshotvertrag und SHA-256 vor jedem Rendern erneut validiert
- [x] Reinen `PdfRenderer` und renderer-neutrale Ausgabebloecke ohne Berichtsdomain wiederverwendet
- [x] Eigenes unveraenderliches LEG-PDF-Artefakt `LCA` mit Dateigroesse, SHA-256 und Erzeugungszeitpunkt modelliert
- [x] Idempotente Wiederaufrufe und Integritaetspruefung vorhandener Artefakte umgesetzt
- [x] PDF-Aktion ausschliesslich in der schreibgeschuetzten aktuellen LEG-Revision vorgesehen
- [x] Tests fuer Snapshotquelle, Draft-Unabhaengigkeit, Hashstabilitaet, Status, Beschädigung und UI-Schichtengrenzen ergaenzt
- [x] Keine Berichtsdomain, Archivierung, Verschluesselung, Renderer-Versionierung, Mehrfachartefakte oder Rollenmodell eingefuehrt
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## Sprint 10A - LEG-Abschluss und Revision ✅

- [x] Bearbeitbaren `LCD` unveraendert als Live-Draft erhalten
- [x] Eigenes stabiles LEG-Aggregat `LCF` und unveraenderliche Revision `LCV` additiv modelliert
- [x] Expliziten Abschluss ueber UI, ViewModel, Adapter, Application Service, Domain, Repository und SQLite gefuehrt
- [x] Pflichtinhalte und ausgewaehlte Referenzen typisiert validiert
- [x] LEG-spezifischen kanonischen Snapshotvertrag und SHA-256-Pruefung umgesetzt
- [x] Identische Abschluesse idempotent behandelt und Korrekturen atomar revisioniert
- [x] Snapshotbasierte schreibgeschuetzte historische Ansicht ergaenzt
- [x] Tests fuer Draft-Erhalt, Integritaet, Revisionierung, Referenzfehler und Schichtengrenzen ergaenzt
- [x] Keine Berichtsdomain, LEG-PDF-, Archivierungs- oder Renderer-Versionierungsfunktion eingefuehrt
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## Sprint 9A - Finaler PDF-Druck aus Berichtrevisionen ✅

- [x] Finalen PDF-Pfad ausschliesslich fuer eine aktuelle `finalized`-Revision (`RPV`) festgelegt
- [x] Snapshot-Integritaet, Status und vollstaendige historische Referenzen vor dem Rendern validiert
- [x] Vorhandenes snapshotbasiertes `ReportOutputModel` und den reinen `PdfRenderer` ohne zweite Berichtsgenerierung wiederverwendet
- [x] Unveraenderliche PDF-Artefaktreferenz mit SHA-256, Dateigroesse und relativem verwaltetem Pfad additiv modelliert
- [x] Studentenzentrierte Ablage ohne Klarname unter `data/documents/<student_id>/reports/<RPT>/<RPV>/` festgelegt
- [x] Finale PDF-Aktion in der schreibgeschuetzten Revisionsansicht fuer die aktuelle Revision vorgesehen
- [x] Fokussierte Tests, Gesamttests, Architekturtests, visuelle PDF-Pruefung und `git diff --check` abgeschlossen
- [x] Keine Renderer-Versionierung, komplexe Archivverwaltung, LEG-PDF oder neuen Berichtsinhalte eingefuehrt
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## UI Sprint 6B - LEG-Workspace umgesetzt ✅

- [x] Bestehenden LEG-Draft als responsiven Sechs-Phasen-Workspace mit stabilem Kontextkopf, kompakter Phasenleiste und persistenter Aktionsleiste neu komponiert
- [x] Vorbereitung, gemeinsam bearbeitete Inhalte und im Draft festgehaltene Vereinbarungen textlich und visuell eindeutig getrennt
- [x] `agreed_goals_text` ohne Persistenz- oder Bedeutungsänderung sichtbar Phase 4 zugeordnet
- [x] Kompetenz-, Beobachtungs- und Diagrammauswahl in Phase 5 konzentriert und in anderen Phasen read-only zusammengefasst
- [x] Zentralen UI-Dirty-State, Inline-Speicherfehler, Toast-Erfolg und sicheren Drei-Wege-Schließen-Ablauf umgesetzt
- [x] Optionalen Überprüfungstermin für neue Drafts tatsächlich leer gelassen und mehrere Drafts ruhig auswählbar gemacht
- [x] Tastatur, Accessible Names, Reduced Motion sowie 1400 x 900, 1280 x 800 und 1180 x 760 automatisiert und offscreen geprüft
- [x] Keine Fachlogik, Schemaänderung, Finalisierung, Revision, Snapshot-, PDF-, Druck- oder Exportfunktion eingeführt
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## UI Sprint 6A - LEG UX Audit und Zielbild ✅

- [x] Bestehenden persistenten LEG-Arbeitsablauf, sechs Phasen, Draft-Wiederaufnahme, Kompetenz-/Belegauswahl, Validierung und Profilnavigation vollstaendig auditiert
- [x] Vorbereitung der Lehrkraft, Gespraechsinhalte und gemeinsam festgehaltene Vereinbarungen im Zielbild eindeutig getrennt
- [x] Kompakte linke Phasennavigation, stabilen Kontext, grosszuegigen Schreibraum und persistente Aktionsleiste fuer UI-Sprint 6B festgelegt
- [x] Responsive Verhalten fuer 1400 x 900, 1280 x 800 und 1180 x 760 sowie Tastatur- und Accessibility-Regeln definiert
- [x] Abschluss, Revisionen, Snapshots, LEG-PDF und Exportartefakte ausdruecklich aus dem Zielbild ausgeschlossen
- [x] Konkreten Implementierungs- und Testschnitt fuer UI-Sprint 6B in `docs/LEG_UX_AUDIT_AND_TARGET.md` dokumentiert

## UI Sprint 5 - Berichtswerkstatt, Finalisierung und Revisionen ✅

- [x] Kompakten Berichtskopf mit Kindkontext, Berichtstyp, Zeitraum, Lehrkraft, Draftstatus und Revisionskontext modernisiert
- [x] Lokale, tastaturfaehige Navigation `Schreiben`, `Kompetenzen & Belege`, `Vorschau`, `Revisionen` umgesetzt
- [x] Gesamttext und Fachtexte als ruhigen Schreibworkspace von Kompetenz-, Beobachtungs- und Diagrammauswahl getrennt
- [x] Historische Kompetenzen und nicht verfuegbare Beobachtungsreferenzen sichtbar erhalten, ohne neue Auswahl oder Rekonstruktion zu erlauben
- [x] Draft-Vorschau dokumentartig und eindeutig als aktueller, gespeicherter oder noch ungespeicherter Entwurf gekennzeichnet
- [x] Finalisierungsdialog, neuestes-zuerst Revisionshistorie und snapshotbasierte finale Leseansicht visuell geschaerft
- [x] Speichern als einzige primaere Draftaktion und Finalisieren als getrennten bewussten Abschluss eingeordnet
- [x] Accessibility, Tastatursteuerung, Reduced Motion sowie 1400 x 900, 1280 x 800 und 1180 x 760 geprueft
- [x] Keine Fachlogik, Datenhaltung, Snapshotauswertung, Revisionsregel oder finales PDF-Artefakt veraendert
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## Sprint 5B.3 - Bericht finalisieren und Revisionen anzeigen ✅

- [x] Bestehende `RPT`-/`RPV`-Revisionen produktiv an die PySide-Berichtswerkstatt angebunden
- [x] Status `Entwurf`, `Finalisiert · Revision X` und `Entwurf geändert` zentral projiziert
- [x] Erst- und Folgerevision mit verpflichtendem Lehrkraft-Anzeigenamen und expliziter Bestaetigung umgesetzt
- [x] Revisionshistorie neueste zuerst mit `Aktuell`, `Ersetzt` und ausschliesslicher Oeffnen-Aktion umgesetzt
- [x] Finale Leseansicht ausschliesslich aus Snapshot, Revisionsmetadaten und gespeichertem Hash umgesetzt
- [x] Snapshotbasierte renderer-neutrale Revisionsprojektion fuer Qt und spaeteren PDF-Sprint bereitgestellt
- [x] Keine Schemaaenderung, kein finales PDF-Artefakt, kein LEG-Abschluss und keine Benutzer-/Rollendomain umgesetzt
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## Sprint 5B.2 - Unveraenderliche Berichtrevisionen im Backend ✅

- [x] Fuenf freigegebene Product-Owner-Entscheidungen verbindlich dokumentiert; Sprint-5A-Vorschlag bleibt nicht bindend
- [x] `RPT-######` als stabiles Berichtaggregat und `RPV-######` als unveraenderliche Revision additiv umgesetzt
- [x] Berichtsspezifischen fachlichen Snapshot mit kanonischem JSON und SHA-256 umgesetzt
- [x] Erstfinalisierung und atomare Folgerevision ueber Validator, Builder, Service, Command und Repository umgesetzt
- [x] Finalisierungs-, Migrations- und Regressionschecks vollstaendig gruen
- [x] Keine UI, kein finales PDF, keine Artefaktverwaltung, kein LEG-Abschluss und keine Benutzer-/Rollendomain vorgesehen

## Sprint 5B.1 - Historische Berichtreferenzen bestandssicher machen ✅

- [x] Gespeicherte, spaeter deaktivierte Berichtskompetenzen ueber `retained_competency_ids` in der kanonischen Projektion sichtbar und ausgewaehlt erhalten
- [x] Neue Auswahl inaktiver oder historischer Kompetenzen unterbunden
- [x] Gespeicherte, spaeter soft-geloeschte Beobachtungsreferenzen als nicht verfuegbar erhalten und neue Auswahl unterbunden
- [x] Explizite Abwahl als einzigen Loeschweg fuer nicht verfuegbare Kompetenz- und Beobachtungsrelationen umgesetzt
- [x] Kind- und Fachzuordnung im Bericht-Repository strikt validiert
- [x] Qt-Vorschau und `ReportOutputModel` um neutrale Ausfallkennzeichnung ohne rekonstruierte Inhalte ergaenzt
- [x] Bestehende Tabellen, IDs, Aggregate, Berichtswerkstatt und PDF-Renderer unveraendert erhalten
- [x] Keine Migration, Finalisierung, Revision, Snapshots, Hashes oder Artefaktverwaltung umgesetzt
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 5A - Product Discovery und Architecture Gate fuer Bericht und LEG ✅

- [x] Bestehende Berichtsvorschau, Text-/Markdown-Export, Berichtswerkstatt, PDF-Weg und LEG mit sechs Phasen analysiert
- [x] Aktuelle Bericht-/LEG-Draftpersistenz, SQLite-Schema, Migrationstechnik, Adapter, ViewModels, Tests und Pilotdaten geprueft
- [x] Konkretes Lebenszyklus-, Snapshot-, Versions-, Korrektur-, Archiv- und Artefaktmodell als nicht bindenden Vorschlag dokumentiert
- [x] Schmale gemeinsame Dokument-/Snapshot-Infrastruktur mit getrennten Bericht-/LEG-Aggregaten empfohlen
- [x] Folge-Sprints und maximal fuenf notwendige Product-Owner-Entscheidungen definiert
- [x] Keine UI-, Produktcode-, Schema-, Migrations-, Test- oder ADR-Aenderung umgesetzt

## UI Sprint 4 - Schuelerprofil, Kompetenz-Cockpit und Beobachtungs-Workspace ✅

- [x] Profilkopf mit dauerhaft sichtbarem Kindkontext und genau einer dominanten Aktion modernisiert
- [x] Lokale Profilnavigation auf zentrale, tastaturfaehige Segmentnavigation umgestellt und Tab-/Scroll-Restaurierung erhalten
- [x] Beobachtungsliste als ruhige, scanbare Card-Liste mit zentraler Suche, sichtbaren Filtern und handlungsorientiertem Leerzustand komponiert
- [x] Kompetenzhierarchie Fach -> Kompetenzbereich -> Thema -> Kompetenz visuell geschaerft und lokale Suche sowie Klassenstufenfilter ergaenzt
- [x] Historische Kompetenzdarstellung und Edit-Autooeffnung unveraendert sichtbar gehalten; neue Auswahl bleibt active/current-only
- [x] Beobachtungsdialog als responsive Drei-Zonen-Arbeitsflaeche mit dauerhaft sichtbarem Speichern, Inline-Validierung und ruhigen Dateizeilen modernisiert
- [x] Disclosure nutzt zentrale kurze Motion-Rueckmeldung; Reduced Motion und schneller Mehrfachwechsel enden unmittelbar korrekt
- [x] Accessibility, Tastatursteuerung und 1400 x 900, 1280 x 800 sowie 1180 x 760 automatisiert und offscreen geprueft
- [x] Keine Datenmodell-, Schema-, Repository-, Bewertungs-, Berichts-, LEG-, Export- oder Legacy-Aenderung
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## UI Sprint 3 - Motion System und Microinteractions ✅

- [x] Motion-Bestand inventarisiert und zentrale Qt-Bordmittel-Architektur festgelegt
- [x] Globale Reduced-Motion-Policy sowie lifecycle-sichere Animationsverwaltung definiert
- [x] Interaktive Karten, Segmentwechsel, Filterchips, Inline-Hinweise und Toasts auf zentrale Motion-API ausgerichtet
- [x] Tabellen, Leerzustaende, Navigation und Dialoge bewusst statisch beziehungsweise nativ belassen
- [x] Keine neue Datenquelle, Fachlogik, Persistenz, Screen-spezifische Animation oder QPainter-Darstellung erforderlich
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## UI Sprint 2 - Premium Components und Workspace Modernization ✅

- [x] Bestehende Komponentenbibliothek inventarisiert und auf kleine semantische V2-Basis ausgerichtet
- [x] `PageHeader`, `SearchField`, `StatusBadge`, `EmptyState`, `SegmentedControl` und `Toast` erweitert
- [x] `AppCard`, `SectionHeader`, `FilterBar`, `FilterChip` und `IconButton` als notwendige neue Basiskomponenten festgelegt
- [x] Scope auf Heute, Schueler-Workspace/-liste, Gruppen-/Kursflaechen und Stammdaten begrenzt
- [x] Keine neue Datenquelle, ViewModel-Verantwortung, Fachlogik oder QPainter-Spezialdarstellung erforderlich
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## UI Sprint 1.1 - Schuelerprofil-Zugriff und Kursansicht ✅

- [x] Einfacher Zeilenklick oeffnet das Schuelerprofil genau einmal
- [x] Doppelklick, Enter und sekundäre Profilaktion ohne Mehrfachnavigation erhalten
- [x] Eingebettete Beobachtungsaktion von der Zeilennavigation getrennt
- [x] Lokale Segmente auf `Stammgruppen`, `Kurse`, `Kursverbünde` und `Alle Schüler` erweitert
- [x] Direkte Kursauswahl nutzt bestehende Kursreihenfolge und `course_id`-Filterprojektion
- [x] Keine Datenmodell-, Schema-, Repository-, Kursverbund- oder Fachlogikaenderung
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## UI Sprint 1 - Product Shell, Informationsarchitektur und Interaction Foundations ✅

- [x] Globale Navigation auf `Heute`, `Schüler`, `Stammdaten` und `Einstellungen` konzentriert
- [x] Fruehere Uebersicht als lokale Segmente `Stammgruppen`, `Kursverbünde` und `Alle Schüler` integriert
- [x] Bestehende Schueler-, Profil-, Beobachtungs-, Kompetenz-, Bericht- und LEG-Pfade erreichbar erhalten
- [x] Design Tokens, native Systemschrift, SVG-Shell-Icons und semantische Buttonrollen eingefuehrt
- [x] `PageHeader`, `SegmentedControl`, `SearchField`, `StatusBadge`, `InlineMessage`, `EmptyState` und `Toast` als Grundkomponenten umgesetzt
- [x] Zeilenauswahl und bewusstes Profiloeffnen getrennt; Fokus-, Tastatur- und Accessibility-Grundlagen ergaenzt
- [x] Dokumentationsmatrix auf neutrale Abstufungen ohne Ampelsemantik umgestellt
- [x] Keine Datenmodell-, Schema-, Migrations-, Adapter-, Repository-, ViewModel- oder Fachlogikaenderung
- [x] Fokussierte UI-Tests, Gesamttests und aktive Build-Pruefung erfolgreich
- [x] Product-Owner-Freigabe durch den vorliegenden Sprintauftrag

## Testdaten - Achtmonatiger produktionsnaher Nutzungsstand ✅

- [x] 24 kuenstliche Kinder auf vier Stammgruppen und drei Kurse verteilt
- [x] Drei Kursverbuende mit unterschiedlichen Stammgruppen-/Kurskombinationen angelegt
- [x] Vollstaendige Unterrichtswoche mit 25 Stammgruppen-, Kurs- und Kursverbundstunden angelegt
- [x] Kompetenzdokumentationen in allen aktiven Katalogfaechern von September bis Juli erzeugt
- [x] Unterschiedliche Dokumentationsdichten, aktuelle Eintraege, Schnellbeobachtungen und Soft Delete enthalten
- [x] Seed-Regressionstest erweitert
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 8B.3 - Passende Kinder als Dokumentationshilfe ✅

- [x] Aktive Kinder aus Stammgruppe, Kurs oder Kursverbund fachbezogen projiziert
- [x] Fehlende, aelteste, kuerzliche und heutige Dokumentation neutral und stabil priorisiert
- [x] Eindeutige Schnellbeobachtungen einbezogen; uneindeutige, soft-geloeschte und fachfremde Beobachtungen ausgeschlossen
- [x] Hoechstens fuenf Vorschlaege mit Name, Hinweis und direktem `Beobachten` umgesetzt
- [x] Fach und Unterrichtskontext in den bestehenden Beobachtungsdialog uebernommen
- [x] Keine Migration, zweite Beobachtungslogik, Kompetenzstatus-, Rating- oder Score-Nutzung
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 8B.2 - Dashboard-Bereiche bereinigt ✅

- [x] Allgemeine Stammgruppen-, Kursverbund- und Schnellzugriffskarten aus Dashboard entfernt
- [x] Dashboard endet nach den unmittelbar stundenbezogenen Bereichen
- [x] Bestehende Uebersicht unveraendert erhalten
- [x] Keine Projektions-, Adapter-, ViewModel-, Persistenz- oder Stundenplanlogik geaendert
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 8B.1 - Dashboard UX-Referenz ✅

- [x] Dashboard als eigenen Hauptnavigationspunkt von der bestehenden Uebersicht getrennt
- [x] Hero-Karte, horizontale Tages-Timeline und kompakte Heatmap-Matrix referenznah umgesetzt
- [x] Passenden Unterrichtskontext und bestehende Schnellzugriffe als getrennte Karten angeordnet
- [x] Stundenplan-, Dashboard-, Adapter-, ViewModel- und Persistenzlogik unveraendert gelassen
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 8B - Stundenplanbasiertes Dashboard ✅

- [x] Kanonische aktuelle, naechste und heutige Stundenprojektion in die Startansicht eingebunden
- [x] Zeit- und Leerzustaende einschliesslich Wochenende und inaktiver Eintraege umgesetzt
- [x] Direkte Navigation fuer Stammgruppe, Kurs und Kursverbund umgesetzt
- [x] Bestehenden Beobachtungsdialog nach Kindauswahl mit Fach und Unterrichtskontext vorbelegt
- [x] Neutrale Dokumentations-Heatmap Stammgruppe × Fach ohne Leistungswerte umgesetzt
- [x] Bestehende Schnellzugriffe erhalten und Dashboard vertikal scrollbar gehalten
- [x] Fokussierte Dashboard-, Stundenplan-, Shell- und Navigationstests ergaenzt
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 7G.3 - Dokumentierte Kompetenzen im LEG ✅

- [x] LEG-Leseprojektion um vorhandene aktive Beobachtungsdaten und aktuelle Bestaetigungsreferenz erweitert
- [x] Sichtbarkeit bei vollstaendig gesetztem Zeitraum auf kompetenzbezogene Beobachtungen im Zeitraum plus aktuelle Bestaetigungen begrenzt
- [x] Ohne vollstaendigen Zeitraum alle dokumentierten Kompetenzen des Kindes sichtbar
- [x] Schnellbeobachtungen, fremde und soft-geloeschte Beobachtungen sowie reine Katalogzeilen ausgeschlossen
- [x] Leere Hierarchiezweige ausgeblendet und ruhigen Fach-Leerzustand ergaenzt
- [x] Bereits ausgewaehlte und historische Draft-Referenzen ausserhalb des Filters sichtbar erhalten
- [x] Zeitraumwechsel ohne automatische Abwahl umgesetzt
- [x] Fokussierte ViewModel-, UI-, Draft-, Adapter- und Projektionspruefungen ergaenzt
- [ ] Historischer Product-Owner-Sichtpruefpunkt: nicht separat dokumentiert

## Sprint 7G.1 - Persistenter LEG-Arbeitsentwurf ✅

- [x] Eigene LEG-Draft-Domain mit `LCD-######`, Schuelerbezug, Zeitraum/Gespraechsdatum, Status `draft`, verantwortlicher Lehrkraft und stabilen Zeitstempeln umgesetzt
- [x] Vollstaendige manuelle Gespraechsstruktur einschliesslich getrennter vorbereiteter und gemeinsam vereinbarter Inhalte modelliert
- [x] Fach-, uebergreifende Themen-, Kompetenz-, Beobachtungs- und Diagrammauswahl als normalisierte Referenzen dokumentiert
- [x] Additive, idempotente SQLite-Migration und Kaskaden fuer abhaengige Draft-Relationen umgesetzt
- [x] Repository, Domain-Service, Application Commands/Queries, Desktop-Adapter und ViewModel-Vorbereitung umgesetzt
- [x] Keine produktive UI-Portierung, finale Dokumentation, Versionierung, Archivierung, Freigabe, Signatur oder PDF-Erzeugung
- [x] Fokussierte LEG-, SQLite- und Adaptertests erfolgreich
- [x] Compile-, Import- und Diff-Pruefung erfolgreich

## Sprint 7G.2 - 1:1 UX-Portierung Lernentwicklungsgespraech ✅

- [x] Freigegebenen Prototyp `prototypes/learning_conference_ux/` ohne neue fachliche Datenmodellentscheidung als produktiven Zwei-Seiten-Arbeitsbereich portiert
- [x] Vorbereitung und Gespraechsmappe, Kartenhierarchie, sechs Phasen, Warnung bei mehr als fuenf Belegen und drei neutrale Visualisierungen uebernommen
- [x] Eindeutigen Profileinstieg sowie kontrollierte Auswahl bei mehreren vorhandenen Drafts umgesetzt
- [x] Alle 7G.1-Texte und Auswahlreferenzen speicher- und rekonstruierbar angebunden
- [x] Aktive aktuelle Kompetenzen neu auswaehlbar; historische und nicht verfuegbare Referenzen kontrolliert sichtbar
- [x] Fokussierte UI-, Draft-, Adapter- und Offscreen-Pruefungen erfolgreich
- [ ] Historischer Product-Owner-Sichtpruefpunkt der produktiven Oberflaeche: nicht separat dokumentiert

## Sprint 7F.2 - 1:1 UX-Portierung Lernentwicklungsbericht ✅

- [x] Oberen Wechsel `Bericht bearbeiten` / `Berichtsvorschau` aus dem freigegebenen Prototyp übernommen
- [x] Linke Arbeitsbereichsnavigation mit Dokumentkontext, Fachseiten und Abschluss übernommen
- [x] Kartenstruktur, Informationshierarchie, Fachtexte, Kompetenzauswahl, Belegauswahl und Vorschaukonzept portiert
- [x] Vorhandene Draft-Persistenz an Öffnen, Laden, Speichern und erneutes Öffnen der Berichtswerkstatt angebunden
- [x] Nur die drei erlaubten neutralen Diagrammtypen auswählbar und ausgabewirksam gemacht
- [x] Keine Änderung an Datenmodell, Repository, Kompetenzprojektion, Beobachtungslogik, Output-Modellklassen oder Renderer
- [x] Fokussierte Bericht-/Draft-/PDF-Tests erfolgreich
- [x] Vollstaendige Regression in spaeteren Gesamttestlaeufen bestaetigt

## Sprint 7F.1 - Persistenter Berichtsentwurf ✅

- [x] Additive SQLite-Migration fuer Berichtsentwurf und normalisierte Auswahlrelationen umgesetzt
- [x] Entwurf mit `RPD-######`, Schuelerbezug, Zeitraum, Status `draft`, Lehrkraft, Gesamtblick und Zeitstempeln angelegt
- [x] Manuelle Fachtexte fuer Staerken, Lernentwicklung, Unterstuetzungsbedarf und naechste Ziele gespeichert
- [x] Fach-, Kompetenz-, Beobachtungs- und Diagrammauswahl als Referenzen gespeichert
- [x] Repository, Domain-Service, Application Commands/Queries, ViewModels und Desktop-Adapter fuer Anlegen, Laden, Aktualisieren und Auflisten umgesetzt
- [x] Kompetenzprojektion, Beobachtungslogik, `ReportOutputModel` und PDF Renderer unveraendert gelassen
- [x] Sprint 7F.2 verbindet die persistente Draft-Struktur mit der 1:1 portierten Berichtswerkstatt-UX

## Sprint 7B - Product- und Architekturentscheidung fuer Bericht, LEG und PDF ✅

- [x] Status: Architekturentscheidung dokumentiert, keine Implementierung

### Ergebnis

- [x] Schuelerprofil als Live-Arbeitsansicht und nicht als offizielles Dokument abgegrenzt
- [x] Bericht als spaetere eigene fachliche Entitaet mit eingefrorenem, versionierbarem Ausgabestand entschieden
- [x] LEG fachlich vom Bericht getrennt und Vorbereitung von spaeter speicherbaren Zielen, Vereinbarungen und Ergebnissen unterschieden
- [x] PDF als rein lesender Renderer fuer eingefrorene Ausgabemodelle festgelegt
- [x] Diagramme auf Dokumentationsabdeckung und Entwicklungsevidenz begrenzt
- [x] Zielarchitektur und zentrale Product-Owner-Entscheidungen in ADR-050 dokumentiert
- [x] Keine UI-, SQLite-, Schema-, Migrations- oder Codeaenderung umgesetzt

### Inzwischen umgesetzter Stand

- [x] Sprint 7F.1 und 7F.2 haben den persistenten Berichtsentwurf und die freigegebene Berichtswerkstatt-UX produktiv umgesetzt
- [x] Sprint 7G.1 bis 7G.3 haben den persistenten LEG-Arbeitsentwurf, die freigegebene LEG-UX und die dokumentierte Kompetenzauswahl produktiv umgesetzt
- [x] Der PDF-Renderer liest weiterhin ausschliesslich ein neutrales Ausgabemodell und greift nicht direkt auf SQLite zu
- [x] Bericht- und LEG-Drafts bleiben bearbeitbare Arbeitsstaende; finale Zustaende werden getrennt als unveraenderliche `RPV`- beziehungsweise `LCV`-Revisionen gefuehrt
- [x] Sprint 9A und Sprint 10B erzeugen getrennte unveraenderliche PDF-Artefakte ausschliesslich aus den jeweils aktuellen verifizierten Revisionen

## Sprint 4B - Lehrplanbasierter Kompetenzkatalog ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Lehrplanbasierte aktuelle Kompetenzen fuer Deutsch, Mathematik, EPU, Musik, Kunst, Sport, Werken, Schulgarten, Ethik und Sozialkompetenz additiv in den CSV-Katalog uebernommen
- [x] Ersetzte Bestandskompetenzen als `legacy` und standardmaessig inaktiv erhalten; historische Beobachtungen und Bestaetigungen bleiben sichtbar
- [x] Globale `CMP-######`-ID-Fortfuehrung, Katalogmetadaten und optionale Sport-Aktivierungsgruppen konsistent dokumentiert
- [x] Religion ausserhalb des Sprint-4-Katalogabgleichs unveraendert gelassen
- [x] Keine UI-, SQLite-, Schema- oder Architekturaenderung im Abschlussabgleich

## Sprint - Schuelerprofil-Ueberblick vor Laura-Pilottest ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Schuelerprofil oeffnet zuerst den Reiter `Überblick`
- [x] `Halbjahresblick` zeigt Beobachtungszahl, Dokumentationsstand und letzte aktive Beobachtung
- [x] Staerken werden nur aus klar positiven vorhandenen Kompetenzdaten abgeleitet
- [x] `Im Blick behalten` nutzt schwaechere Verlaeufe oder wenig dokumentierte Bereiche als Beobachtungshinweis
- [x] Letzte Beobachtungen, kompakter Dokumentationsstand und sichtbare Entwicklung stehen im Ueberblick
- [x] Bestehende Details bleiben ueber `Beobachtungen`, `Kompetenzen`, `Bericht` und `Dateien` erreichbar
- [x] Laura-Pilottestpunkte zum Schuelerprofil wurden aktualisiert statt doppelt ergaenzt
- [x] Keine neue Persistenz, keine Schemaaenderung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Schnellbeobachtung und Zurueck-Navigation ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Schuelerlisten zeigen je Schueler eine kompakte Aktion `Beobachten`
- [x] Schnellaktion oeffnet den bestehenden Beobachtungsdialog fuer genau diesen Schueler
- [x] Speichern laeuft weiter ueber bestehende Adapter-/Service-/Repository-Struktur
- [x] Nach Speichern werden Schuelerliste, Uebersicht und Dokumentationsstatus aktualisiert
- [x] Gefilterte Stammgruppen-/Kurs-/Kursverbund-Listen zeigen `← Zur Übersicht`
- [x] Keine neue Beobachtungslogik, keine Schemaaenderung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Excel/VBA-Legacy bereinigen ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Reine Excel-/openpyxl-/VBA-Dateien nach `legacy/excel/` verschoben
- [x] Alter Excel/VBA-CLI-Bridge-Adapter `km.py` samt Test nach `legacy/excel/` verschoben
- [x] Aktive Referenzdaten aus `src/core/workbook_data.py` nach `src/core/records.py` entkoppelt
- [x] Aktive Tests von Workbook-/openpyxl-Projektionen getrennt
- [x] `output/.gitkeep` entfernt; Runtime-/Output-Dateien bleiben unversioniert
- [x] README und Governance-Dokumente beschreiben PySide/SQLite als aktiven Hauptpfad
- [x] `python3 build.py` ist kein Pflichtcheck mehr; Standardcheck nutzt PySide-/SQLite-Tests und Offscreen-Import

## Sprint - Berichtsvorschau und Halbjahres-Testdaten ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Berichtsentwicklung wird aus chronologischen aktiven Beobachtungen abgeleitet
- [x] Einzelbeobachtung, stabile Entwicklung, positive Entwicklung, Rueckschritt und wechselnde Beobachtungslage werden verstaendlich formuliert
- [x] Soft-geloeschte Beobachtungen fliessen nicht in Berichtsentwicklung ein
- [x] Leere Berichtsvorschau zeigt `Noch keine Beobachtungen dokumentiert.`
- [x] `scripts/seed_test_data.py` erzeugt halbjaehrliche Pilottestdaten von September bis Januar
- [x] Testdaten enthalten mehrere Verlaufsmuster, bestaetigte Kompetenzstaende, Abweichungen, Dokumente und unterschiedlich dichte Dokumentationsstaende
- [x] Keine KI-Textgenerierung, keine Schemaaenderung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Dokumentationsstatus kompakt in Schuelerlisten ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Schuelerlisten zeigen je Schueler eine kompakte Dokumentationssummary
- [x] Schuelerlisten zeigen keine vollstaendige Fachaufschluesselung
- [x] Schuelerprofil zeigt den Dokumentationsstand standardmaessig kompakt
- [x] Fachdetails im Dokumentationsstand sind per `Details anzeigen` aufklappbar
- [x] Dokumentierte Lernbereiche zaehlen aktive Beobachtungen und bestaetigte Kompetenzstaende
- [x] Soft-geloeschte Beobachtungen zaehlen nicht
- [x] Keine neue Persistenz, keine Schemaaenderung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Laura-Pilottestdaten fuer SQLite ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] `scripts/seed_test_data.py` fuer die aktuelle SQLite-Datenbank ergaenzt
- [x] Standardlauf bricht bei vorhandenen Schuelern, Beobachtungen oder Dokumenten ab
- [x] `--reset` erzeugt bewusst ein frisches Testsystem
- [x] Testdaten decken Stammgruppen, Kurse, Kursverbuende, Schuelerlisten-Sortierung, Beobachtungen, Kompetenzvorschlaege, Bestaetigungen, Berichtsvorbereitung, Dokumentationsstand und Dokumente & Medien ab
- [x] Demo-Dateien werden als harmlose Platzhalter unter `data/documents/` erzeugt
- [x] Keine echten Namen, keine echten Dokumente, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Dokumente & Medien MVP ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Dokumente und Medien koennen einem Schueler zugeordnet werden
- [x] Beobachtungsdialog kann Dateien beim Anlegen/Bearbeiten hinzufuegen und entfernen
- [x] SQLite speichert nur Metadaten in `documents`, keine Datei-BLOBs
- [x] Dateien werden studentenzentriert unter `data/documents/<student_id>/` abgelegt
- [x] Schuelerprofil zeigt alle aktiven Dokumente und Medien neueste oben
- [x] Aufgeklappte Beobachtungskarten zeigen verknuepfte Anhaenge
- [x] Keine PDF-Erstellung, keine Vorschau, keine Berichte-Erweiterung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Dokumentationsstand im Schuelerprofil ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Dokumentationsstand zeigt pro Fach dokumentierte Kompetenzen im Verhaeltnis zum aktiven Katalog
- [x] Aktive Beobachtungen und bestaetigte Kompetenzstaende zaehlen als dokumentiert
- [x] Soft-geloeschte Beobachtungen zaehlen nicht
- [x] Fehlende Kompetenzen koennen pro Fachgruppe aufgeklappt werden
- [x] Keine neue Persistenz, keine Schemaaenderung, keine Dokumentenverwaltung, keine Berichtserweiterung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Berichtsvorschau kopieren und Text exportieren ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Berichtsvorschau kann im Schuelerprofil kopiert werden
- [x] Berichtsvorschau kann als einfache Text-/Markdown-Datei exportiert werden
- [x] Text enthaelt Schuelername, Stammgruppe, Kurs, Erstellungsdatum, Fachgruppen, Kompetenzstaende und Beobachtungsbelege
- [x] Bestaetigte Kompetenzstaende werden vor berechneten Vorschlaegen genutzt
- [x] Soft-geloeschte Beobachtungen erscheinen nicht
- [x] Keine PDF-/Word-Erstellung, keine KI-Textgenerierung, keine neue Persistenz, kein Excel/VBA und kein Commit umgesetzt

## Sprint B - Berichtsvorbereitung aus Kompetenzstaenden und Beobachtungen ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Schuelerprofil zeigt eine abgeleitete Berichtsvorschau nach Fach
- [x] Bestaetigte Kompetenzstaende werden vor berechneten Vorschlaegen genutzt
- [x] Ohne Bestaetigung wird der berechnete Vorschlag verwendet
- [x] Stärken, Entwicklung, Unterstützungsbedarf und Beispielbeobachtungen werden strukturiert angezeigt
- [x] Soft-geloeschte Beobachtungen fliessen nicht ein
- [x] Keine KI-Textgenerierung, kein Export, keine neue Persistenz, kein Excel/VBA und kein Commit umgesetzt

## Sprint A - Bestaetigten Kompetenzstand speichern ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Bestaetigter Kompetenzstand wird pro `student_id` und `competency_id` in SQLite gespeichert
- [x] Vorschlag bleibt berechnet und sichtbar
- [x] Lehrkraft kann Vorschlag uebernehmen oder manuell `++`, `+`, `-`, `--` bestaetigen
- [x] Abweichung zwischen Vorschlag und Bestaetigung wird angezeigt
- [x] Neuerer Vorschlag nach bestehender Bestaetigung wird sichtbar markiert
- [x] Beobachtungen werden nicht veraendert
- [x] Keine Berichte, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Kompetenzvorschlag und Fachgruppen im Schuelerprofil ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Kompetenzuebersicht zeigt Faecher kompakt und aufklappbar
- [x] Kompetenzuebersicht berechnet Vorschlag aus allen aktiven Beobachtungen
- [x] Soft-geloeschte Beobachtungen fliessen nicht in den Stand ein
- [x] Bewertungsverlauf wird chronologisch angezeigt
- [x] Anzahl Beobachtungen und neuestes Beobachtungsdatum werden pro Kompetenz angezeigt
- [x] Berechnung bleibt abgeleitet und wird nicht gespeichert
- [x] Folgethema dokumentiert: Lehrkraft kann Vorschlag spaeter bestaetigen oder manuell anpassen
- [x] Beobachtungsverlauf, Persistenz, Schema, Berichte und Excel/VBA unveraendert

## Sprint - Kursverbund anlegen und Schuelerlisten sortieren ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] `+ Kursverbund` in den PySide-Stammdaten angebunden
- [x] Neuer Kursverbund nutzt den bestehenden Kursverbund-Dialog mit Name, Stammgruppen und Kursen
- [x] Speichern persistiert den neuen Kursverbund in SQLite
- [x] Neuer Kursverbund erscheint nach dem Speichern in Stammdaten und Uebersicht
- [x] Duplikate mit gleichem Kursverbundnamen werden abgefangen
- [x] Schuelerlisten werden zentral nach Kursreihenfolge und danach alphabetisch sortiert
- [x] Schueler ohne bekannten aktiven Kurs stehen am Ende
- [x] Kursverbund-Filterlogik, Schema, Beobachtungen, Medien und Excel/VBA unveraendert

## UI-Polish - Beobachtungsverlauf im Schuelerprofil beruhigen ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Ohne aktive Filter werden nur die drei neuesten Beobachtungen gezeigt
- [x] `Alle Beobachtungen anzeigen (X)` erweitert den Verlauf
- [x] `Weniger anzeigen` reduziert wieder auf drei Beobachtungen
- [x] Aktive Filter und Suche durchsuchen weiterhin alle Beobachtungen
- [x] Details-, Reset- und Filteraktionen sind optisch dezenter
- [x] Bewertungsfilter ist lesbarer; ComboBox-/Dropdown-Stil gilt app-weit ruhiger
- [x] Datum-, Zeit- und Datum-Zeit-Felder sind an den globalen Dropdown-Stil angeglichen
- [x] Kompetenzuebersicht, Persistenz, Schema und Excel/VBA unveraendert

## UI-Polish - Beobachtungen im Schuelerprofil filtern ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Beobachtungsverlauf kann nach Fach inklusive `Fächerübergreifend` gefiltert werden
- [x] Bewertungsfilter zeigt Beobachtungen mit passender Kompetenzbewertung
- [x] Suche prueft Kontext, Notiz und Kompetenznamen
- [x] Reset setzt alle Beobachtungsfilter zurueck
- [x] Kompetenzuebersicht, Persistenz, Schema, Excel/VBA und Bearbeiten/Loeschen unveraendert

## UI-Polish - Aufklappbare Beobachtungskarten ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Beobachtungskarten starten kompakt mit Datum, Fach, Kontext, Notizvorschau und Kompetenzanzahl
- [x] Details lassen sich pro Karte aufklappen
- [x] Aufgeklappt bleiben volle Notiz, Kompetenzbewertungen sowie Bearbeiten/Loeschen erreichbar
- [x] Kompetenzuebersicht, Persistenz, Schema, Excel/VBA und Sortierung unveraendert

## Sprint - Beobachtungen bearbeiten und löschen ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Beobachtungen koennen aus dem Schuelerprofil heraus zum Bearbeiten geoeffnet werden
- [x] Datum, Kontext, Notiz, Kompetenzen und Bewertungen werden aktualisiert
- [x] Kompetenzbewertungen werden beim Speichern atomar ersetzt
- [x] Loeschen setzt `observations.active = 0`
- [x] Beobachtungsliste und Kompetenzuebersicht laden danach aktive Beobachtungen neu
- [x] Multi-Fach-Fachanzeige wird aus den Kompetenzfaechern neu berechnet
- [x] Keine Medien, keine Berichte, kein UI-Redesign, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Kompetenzen SQLite-persistent machen ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] SQLite-Tabelle `competencies` ergaenzt
- [x] Katalog-Seed aus `data/curriculum_catalog_v1.csv` laeuft nur bei leerem Kompetenzkatalog
- [x] Beobachtungen referenzieren weiter `competency_id`
- [x] Schuelerprofil zeigt beobachtete Kompetenzen gruppiert nach Fach
- [x] Letzte Bewertung je Kompetenz wird aus Beobachtungen abgeleitet
- [x] Keine freie Kompetenzbearbeitung, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Kompetenzkatalog fachlich stabilisieren ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] `competency_id` als explizites Katalogfeld ergaenzt
- [x] Katalogeintraege validieren stabile ID, Fach und lesbare Labels
- [x] Kompetenzen koennen nach Fach gruppiert gelesen werden
- [x] EPU bleibt UI-Name, Sozialkompetenz bleibt eigener Bereich
- [x] Keine freie Kompetenzbearbeitung, keine Schema-Migration, kein Excel/VBA und kein Commit umgesetzt

## Korrektur - Fachanzeige bei Multi-Fach-Beobachtungen ✅

- [x] Status: Abgeschlossen

### Ergebnis

- [x] Schuelerprofil-Fachanzeige aus Kompetenzbewertungen abgeleitet
- [x] Ein-Fach-Beobachtungen zeigen das gemeinsame Fach
- [x] Multi-Fach-Beobachtungen zeigen `Fächerübergreifend`
- [x] Einzelne Kompetenzbewertungen behalten ihr Fachlabel
- [x] Keine Schema-Migration, kein Excel/VBA und kein Commit umgesetzt

## Sprint - Beobachtungen SQLite-Persistenz ✅

- [x] Status: Abgeschlossen

### Titel

Beobachtungen persistent speichern und nach Neustart laden

### Ergebnis

- [x] SQLite-Tabellen fuer Beobachtungen und Kompetenzbewertungen ergaenzt
- [x] Beobachtungen werden ueber `observation.create` atomar in SQLite gespeichert
- [x] Mehrere Kompetenzen mit jeweils eigener Bewertung werden gespeichert und geladen
- [x] Schuelerprofil zeigt persistente Beobachtungen nach Adapter-/App-Neustart
- [x] Dialog speichert ueber Adapter, Service, Repository und nicht direkt in Qt-Widgets
- [x] Keine Medien, Berichte, Export, Packaging, Excel/VBA oder UI-Redesign geaendert

## Sprint - Schuelerdaten SQLite-Persistenz ✅

- [x] Status: Abgeschlossen

### Titel

Schuelerdaten persistent speichern und nach Neustart laden

### Ergebnis

- [x] Bestehende `students`-Tabelle und `SQLiteStudentRepository` geprueft
- [x] Produktiver App-Start erzeugt keine Demo-Schueler mehr
- [x] Neue Schueler werden ueber `student.create` in SQLite gespeichert
- [x] Reload ueber neuen `StudentDesktopAdapter` laedt gespeicherte Schueler
- [x] Schuelerliste, Suche, Profil, Stammgruppenfilter und Kursverbundfilter mit persistenten Schuelern getestet
- [x] Keine Beobachtungspersistenz, Medien, Berichte, Packaging, Excel/VBA oder UI-Redesign geaendert

## Sprint - Stammdaten und Kursverbuende SQLite-Persistenz ✅

- [x] Status: Abgeschlossen

### Titel

Stammdaten und Kursverbuende in SQLite speichern

### Ergebnis

- [x] SQLite-Schema fuer Kursverbuende und Relationstabellen ergaenzt
- [x] Gruppen und Kurse um Sortierung sowie Kursfarben-Metadaten erweitert
- [x] Persistentes Repository fuer Stammdaten und Kursverbuende umgesetzt
- [x] Default-Stammdaten werden nur bei leerem Stammdaten-Scope erzeugt
- [x] `MasterDataDesktopAdapter` laedt und speichert Stammdaten ueber SQLite
- [x] Kursverbund-Updates speichern Name, Stammgruppen- und Kurszuordnung atomar
- [x] Keine Beobachtungspersistenz, keine Medien, keine Berichte, kein Excel/VBA und kein Packaging geaendert

## Sprint - PySide Icon Branding und Glas-Polish ✅

- [x] Status: Abgeschlossen

### Titel

App-Icon sichtbar machen und dezente Glasoptik erweitern

### Ergebnis

- [x] App-Icon als versioniertes Asset `assets/app_icon.png` abgelegt
- [x] Zentralen Icon-Helfer fuer Pfad, Pixmap und Label ergaenzt
- [x] Icon oben in der Sidebar sichtbar eingebunden
- [x] Icon oben zentriert im App-Info-Dialog sichtbar eingebunden
- [x] Zentrales Theme um dezente Glas-/Polish-Regeln erweitert
- [x] Keine Fachlogik, keine Persistenz, kein Excel/VBA und kein Packaging geaendert

## Sprint - PySide Icon Theme ✅

- [x] Status: Abgeschlossen

### Titel

Icon-basierte visuelle Anpassung der PySide-Hauptanwendung

### Ergebnis

- [x] Zentrales PySide-Theme aus der freigegebenen Icon-Farbwelt erstellt
- [x] App-weites Stylesheet fuer Navigation, Karten, Tabellen, Eingaben und Dialoge angebunden
- [x] Bestehende PySide-Screens und Dialoge auf semantische Text- und Card-Helfer umgestellt
- [x] Kursfarbmarker als fachliche Marker erhalten
- [x] Keine Fachlogik, keine Persistenz und kein Excel-/VBA-Pfad geaendert

## Historische Excel-/Workbook-Sprints

Die folgenden Sprintstaende dokumentieren die fruehere Excel-/Workbook-Produktlinie. Sie sind beendet oder durch die produktive PySide-/SQLite-Anwendung abgeloest und gehoeren nicht mehr zur aktiven Sprintplanung. Offene Checkboxen bleiben als historische Pruef- oder Planungsreste sichtbar.

## Sprint 0 - Historische Projektgrundlage ✅

- [x] Status: Abgeschlossen

### Ziele

- [x] Projektstruktur erstellt
- [x] Git eingerichtet
- [x] Dokumentation angelegt
- [x] build.py erstellt
- [x] Python-Projekt lauffähig

### Ergebnis

Das Projekt kann erfolgreich mit

```bash
python3 build.py
```

gestartet werden.

## Sprint 1 - Historischer Excel-Generator-Spike 🗂️

- [x] Status: Historischer Spike beendet; durch die PySide-/SQLite-Produktlinie abgeloest

### Titel

Excel-Generator

### Ziele

- [x] Build-Architektur erstellen
- [x] Workbook-Generator implementieren
- [x] Erste Excel-Datei erzeugen
- [x] Dashboard-Blatt erstellen
- [x] Schüler-Blatt erstellen
- [x] Kompetenzen-Blatt erstellen
- [x] Bewertungen-Blatt erstellen
- [x] Einstellungen-Blatt erstellen
- [x] Changelog-Blatt erstellen

### Akzeptanzkriterien

- [x] python3 build.py läuft fehlerfrei
- [x] output/Jenaplan_v3.2.xlsx wird erzeugt
- [ ] Datei lässt sich in Excel öffnen

## Sprint 2 - Historisches Dashboard- und Designkonzept 🗂️

- [x] Status: Historischer Konzeptstand; durch das PySide-Design-System abgeloest

Dashboard & Design

## Sprint 3 - Historischer Excel-UX-Prototyp 🗂️

- [x] Status: Historischer Prototypstand; nicht mehr aktive Zielplattform

Architekturwechsel UX-Prototyp

- [x] Bestehender UX-Prototyp bleibt als First Attempt erhalten
- [x] Neue UX-Prototyp-Version v0.2 vorbereitet
- [x] Zielplattform Microsoft Excel für macOS dokumentiert
- [x] UI-Technologie-ADR ergänzt
- [x] Projektstruktur für spätere Trennung vorbereitet
- [x] Sprint 3.1: Klassenübersicht bauen
- [x] v0.2 enthält keine weiteren Bildschirme
- [x] UI-Anker für spätere VBA-Interaktion vorbereitet
- [ ] Review durch Laura

## Sprint 4.0 ✅

- [x] Status: Abgeschlossen

### Titel

Core Data Architecture

### Ergebnis

- [x] Projektverfassung dokumentiert
- [x] Technical Naming Registry dokumentiert
- [x] Workbook Data Registry dokumentiert
- [x] UI Data Mapping dokumentiert
- [x] View Data Ownership dokumentiert
- [x] Data Lifecycle dokumentiert

## Sprint 4.1 ✅

- [x] Status: Abgeschlossen

### Titel

Schülerverwaltung Phase 1: Architektur validieren

### Ergebnis

- [x] Architektur erfolgreich validiert
- [x] Hidden Data Sheets erzeugt
- [x] `tbl_students`, `tbl_groups`, `tbl_courses` erzeugt
- [x] Stammgruppenübersicht aus Daten projiziert
- [x] Schülerprofil aus Daten projiziert
- [x] VBA-Navigation über `student_id` bleibt funktionsfähig
- [x] Release `v0.4` vorbereitet

## Sprint 4.2 - Historischer transaktionaler Schreibprozess 🗂️

- [x] Status: Historischer Plan; produktiver Schreibprozess spaeter ueber PySide, Application Layer und SQLite umgesetzt

### Titel

Schülerverwaltung: erster transaktionaler Schreibprozess

### Ziele

- [ ] Schüler anlegen
- [ ] Schüler ändern
- [ ] Schüler archivieren
- [ ] Keine physische Löschung
- [ ] Schreibprozess vollständig oder gar nicht ausführen

## Sprint 5 - Historisches Excel-Dialog-Framework 🗂️

- [x] Status: Historischer Scope; VBA-/Worksheet-Dialogpfad beendet und durch PySide-Dialoge abgeloest

### Titel

Dialog Framework, Schuelerverwaltung und Dokumentenarchitektur

### Ziele

- [x] Scope Freeze abschliessen
- [x] Standard fuer modale VBA-UserForms dokumentieren
- [x] Referenzdialog `Neuer Schueler` als erste Referenzimplementierung einordnen
- [x] Dokumentenstruktur fuer Schuelerdokumente und Beobachtungsanhaenge festlegen
- [x] Dokumentbereich in der Schueler-UserForm vorbereiten
- [x] UX-Prototyp fuer Feature 1 `Neuer Schueler` als verbindliche visuelle Vorlage vorbereiten
- [x] UX-Prototyp als Pflichtschritt vor kuenftiger Dialogumsetzung dokumentieren
- [x] VBA-UserForm-Ansatz fuer Excel auf macOS als nicht belastbar bewertet
- [x] Worksheet-basierte Dialogseite `dlg_neuer_schueler` als neuen Feature-1-Pfad vorbereitet
- [x] Spaeteren Beobachtungsdialog mit Kompetenzbezug vorbereiten
- [ ] Produktive Speicherlogik fuer Schueler freigeben

### Sprint 5.1a - Dialog Framework vorbereiten

- [x] Dialogstandard konkretisieren
- [x] `frm_student_new` gegen den Dialogstandard pruefen
- [x] Enter = Speichern und Esc = Abbrechen im Referenzdialog vorbereiten
- [x] Vorgesehenen Dialogoeffner `OpenNewStudentDialog()` registrieren
- [x] Keine produktive Schueler-Speicherlogik
- [x] Kein Seed-Import

### Sprint 5.1b - Schueleranlage ueber UserForm anbinden

- [x] Architekturpfad UserForm -> `StudentService.create_student()` geprueft
- [x] Fehlende freigegebene VBA-zu-Python-Service-Bruecke dokumentiert
- [x] Direkte VBA-Schreiblogik in `tbl_students` ausgeschlossen
- [x] Technische Optionen dokumentiert
- [x] Empfehlung: Command-Queue-Architekturspike
- [x] Keine produktive UserForm-Anbindung umgesetzt
- [x] Kein Seed-Import

### Sprint 5.2a - SQLite Architecture Spike

- [x] SQLite-Verfuegbarkeit geprueft
- [x] Datenbankpfad `data/kompetenzmanager.sqlite` festgelegt
- [x] Tabellen `students`, `groups` und `courses` erzeugt
- [x] Seed-Daten ohne ID-Neuvergabe nach SQLite geschrieben
- [x] SQLite-Repositories fuer Students, Groups und Courses prototypisiert
- [x] Bestehende Excel-Projektion testweise aus SQLite-Daten erzeugt
- [x] Keine produktive Migration
- [x] Keine VBA-zu-Python-Bridge
- [x] Kein Seed-Import

### Sprint 5.3 - Application Command Layer

- [x] Application-Layer-Struktur unter `src/application/` angelegt
- [x] Application Command Dispatcher als Architektur-Skelett eingefuehrt
- [x] `student.create` als erstes Command-DTO vorbereitet
- [x] CLI als spaeteren Adapter dokumentiert
- [x] VBA-Anbindung als spaeteren Command Adapter dokumentiert
- [x] Keine produktive CLI
- [x] Keine UserForm-Anbindung
- [x] Keine Build-Aenderung

### Sprint 5.4 - student.create End-to-End

- [x] `student.create` durch Dispatcher, Command, Service, Repository und SQLite validiert
- [x] `SuccessResult` und `ErrorResult` eingefuehrt
- [x] Keine CLI
- [x] Keine VBA-Anbindung
- [x] Keine Excel-Automation
- [x] Kein Build

### Architecture Baseline v2.0

- [x] Validierten Sprint-5-Architekturstand dokumentiert
- [x] Architecture v1 historisch eingeordnet
- [x] Adapter, Application, Domain, Infrastructure, Projection und Excel UI als Schichten beschrieben
- [x] Standard-Datenfluss dokumentiert
- [x] Keine neue Implementierung

### Feature 1 - UX-Prototyp `Neuer Schueler`

- [x] `output/Jenaplan_UX_Prototype_v0.1.xlsx` um das Blatt `Feature 1 – Neuer Schüler` ergaenzt
- [x] Fenstertitel, Pflichtfelder, Notizbereich, Dokumentbereich, Dokument-Hinzufuegen-Button sowie Abbrechen/Speichern visuell dargestellt
- [x] Blatt als visuelle Vorlage fuer den spaeteren Eingabedialog dokumentiert
- [x] Keine VBA-UserForm, keine Python-Aenderung, keine Validierung, keine Adapter-Anbindung und kein Build umgesetzt
- [ ] UX-Review mit Laura bzw. Product Owner durchfuehren
- [ ] UX-Freigabe vor technischer Dialogumsetzung dokumentieren

### Feature 1 - Architekturwechsel zu `dlg_neuer_schueler`

- [x] VBA-UserForms auf Excel fuer macOS als instabil bewertet
- [x] `frm_student_new` als experimentell/deprecated eingeordnet
- [x] Worksheet-basierte Dialogseiten als primaeres Eingabe-Pattern dokumentiert
- [x] `dlg_neuer_schueler` als Dialogseite fuer `Neuer Schueler` vorbereitet
- [x] Absprungpunkt `+ Schüler` von der Stammgruppenuebersicht zur Dialogseite vorbereitet
- [x] Keine Speicherlogik, keine Validierung, kein Python-Command und kein SQLite-Schreibzugriff umgesetzt

### Feature 1.3 - Dialogseite vorbereiten

- [x] Dialogseite `dlg_neuer_schueler` bleibt geschuetzt
- [x] Nur Eingabebereiche fuer Vorname, Nachname, Stammgruppe, Kurs und Notiz entsperrt
- [x] Eingabebereiche ueber registrierte Named Ranges vorbereitet
- [x] Abbrechen als Navigation zur Stammgruppenuebersicht vorbereitet
- [x] Speichern optisch vorbereitet, aber ohne Aktion
- [x] Dokumentbereich sichtbar, `+ Dokument hinzufügen` ohne Funktion
- [x] Keine Speicherung, keine Validierung, kein Python-Command und kein SQLite-Schreibzugriff umgesetzt

### Feature 1.4a - Runtime Adapter und Refresh Contract

- [x] Runtime-Pfad `Dialogseite -> VBA Adapter -> Python CLI/Bridge -> Dispatcher -> StudentService -> Repository -> SQLite` freigegeben
- [x] Refresh Contract ueber Python-generiertes Projection-Refresh-Paket freigegeben
- [x] VBA darf nur Projection Output importieren und keine fachliche Tabellenlogik ausfuehren
- [x] SQLite als Source of Truth fuer `student.create` im Feature-1-Schreibprozess festgelegt
- [x] Feature 1.4 darf implementiert werden, wenn dieser Vertrag eingehalten wird
- [x] Keine Speicherung, keine Validierung, kein Python-Aufruf aus VBA und kein Workbook-Refresh umgesetzt

### Feature 1.4b - Produktiver Speichervorgang bis SQLite

- [x] `SaveNewStudentDialog()` als VBA Adapter fuer die Dialogseite umgesetzt
- [x] Adapter liest ausschliesslich registrierte Named Ranges von `dlg_neuer_schueler`
- [x] Adapter schreibt `runtime_command.json` und startet `km.py student create`
- [x] `km.py` verwendet `ApplicationCommandDispatcher`, `CreateStudentCommand`, `StudentService` und `SQLiteStudentRepository`
- [x] `student.create` schreibt produktiv in `data/kompetenzmanager.sqlite`
- [x] Erfolg und Fehler werden ueber `runtime_result.json` an Excel zurueckgegeben
- [x] Noch kein Projection Refresh, keine Workbook-Aktualisierung und keine Navigation nach dem Speichern umgesetzt

### Spike - PySide6 Desktop-App als alternativer Adapter

- [x] Branch `spike/python-gui` genutzt
- [x] Ruecksprungpunkt `checkpoint-excel-adapter-before-python-gui` bleibt fuer Excel/xlwings erhalten
- [x] PySide6 statt tkinter als Spike-UI verwendet
- [x] App `Jenaplan Kompetenzmanager` startet
- [x] Maske `Neuer Schüler` funktioniert
- [x] Schueler wird ueber `CreateStudentCommand`, `ApplicationCommandDispatcher`, `StudentService` und `SQLiteStudentRepository` in SQLite geschrieben
- [x] Keine Businesslogik in der GUI
- [x] Kein direkter SQLite-Write aus Qt Widgets
- [x] Tests gruen: 26 passed
- [x] Build gruen
- [x] Commit `5363e18` und Tag `spike-pyside6-student-create` gesetzt
- [x] Durch ADR-046 entschieden: PySide ist Hauptanwendung
- [x] Durch ADR-046 entschieden: Excel/VBA ist Export-, Berichts-, Referenz- oder Legacy-Pfad
- [x] Durch ADR-046 entschieden: xlwings/Excel-Bruecke ist kein Zielpfad fuer neue Haupt-App-Features

### GUI-Umsetzungspruefung 1 - PySide6 App-Struktur und MVP-Navigation

- [x] PySide6 als moegliche Hauptanwendung fachlich und technisch geprueft
- [x] Ziel-App-Struktur fuer Hauptfenster, Navigation, Schuelerliste, Schuelerprofil light und Platzhalterbereiche skizziert
- [x] MVP-Schnitt ohne Beobachtungsmaske, Packaging und Excel-Export-Umbau definiert
- [x] Design-System-Uebertragung auf PySide6 dokumentiert
- [x] Risiken fuer Packaging, Datenbankpfad, Backup/Restore, Updates, Excel-Export und Testbarkeit bewertet
- [x] Nutzen-Aufwand-Vergleich fuer PySide6, xlwings und Excel/VBA-Runtime-Adapter dokumentiert
- [x] Keine finale Architekturentscheidung getroffen
- [x] Keine Feature-Implementierung umgesetzt

### Sprint - PySide6 MVP Shell und Navigation

- [x] Hauptfenster `Jenaplan Kompetenzmanager` mit Navigation umgesetzt
- [x] Navigationspunkte `Übersicht`, `Schüler`, `Beobachtungen`, `Kompetenzen`, `Berichte` und `Einstellungen` umgesetzt
- [x] Uebersicht mit Stammgruppen-/Gruppenkarten und Schuelerzahlen umgesetzt
- [x] Schuelerseite mit SQLite-Schuelerliste umgesetzt
- [x] Bestehenden Dialog `+ Schüler` integriert
- [x] Schuelerprofil light mit Stammdaten und Notiz umgesetzt
- [x] Platzhalter fuer Beobachtungen, Kompetenzen, Berichte und Einstellungen umgesetzt
- [x] Keine Beobachtungsmaske, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Sprint - PySide6 UX Stabilisierung 1

- [x] Zurueck-Button im Schuelerprofil light umgesetzt
- [x] Ruecksprung zur Schuelerliste erhaelt den aktuellen Gruppenfilter
- [x] Klick auf `Schüler` in der linken Navigation fuehrt aus dem Profil zur Liste
- [x] Schuelerprofil in Titel, Stammgruppe/Kurs, Notiz und Beobachtungsplatzhalter gegliedert
- [x] Nicht-modale Statusmeldung `Schüler wurde gespeichert.` nach erfolgreichem Speichern ergaenzt
- [x] Suche in der Schueleruebersicht ergaenzt
- [x] Suche filtert nach Vorname, Nachname, Vollname, Stammgruppe und Kurs
- [x] Suche bleibt mit Gruppenfilter kombinierbar
- [x] Keine Beobachtungsmaske, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Sprint - PySide6 Schuelerprofil UX-Ausbau 1

- [x] Profilkopf mit Zurueck-Button, Name, Stammgruppe, Kurs und dezenter `student_id`-Anzeige umgesetzt
- [x] Schnellaktionen `+ Beobachtung`, `Dokument hinzufügen` und `Schüler bearbeiten` sichtbar gemacht
- [x] Schnellaktionen bleiben reine Platzhalter mit Inline-Hinweis und starten keine produktiven Fachprozesse
- [x] Basisdaten als eigener Profilbereich umgesetzt
- [x] Beobachtungen, Kompetenzen und Dokumente als Karten mit Platzhaltertexten strukturiert
- [x] Keine Beobachtungsmaske, keine Beobachtungspersistenz, keine Dokumentenverwaltung und keine Kompetenzberechnung umgesetzt
- [x] Keine Datenmodelländerung, kein Packaging und kein Excel-Export-Umbau umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Sprint - PySide6 Beobachtungsdialog UX-Prototyp 1

- [x] `+ Beobachtung` im Schuelerprofil oeffnet einen nicht-persistenten Dialog `Neue Beobachtung`
- [x] Dialog zeigt den ausgewaehlten Schueler sichtbar im Titelbereich
- [x] Felder fuer Datum, Fach, Kompetenz(en), Kontext, Bewertung und Notiz umgesetzt
- [x] Bereich `Dokumente & Medien` mit Hinweis, `Datei hinzufügen` und Empty State vorbereitet
- [x] Speichern zeigt nur den Hinweis, dass Beobachtungen spaeter gespeichert werden
- [x] `Datei hinzufügen` zeigt nur den Hinweis, dass Anhaenge spaeter gespeichert werden
- [x] Lokale UI-Listen fuer Fach und Kompetenzen als Spike-Einschraenkung verwendet
- [x] Keine Beobachtungspersistenz, kein Repository, keine SQLite-Aenderung und keine Datenmodelländerung umgesetzt
- [x] Keine Dokumentenanhaenge, kein Packaging, kein Excel-Export-Umbau und keine finale Architekturentscheidung umgesetzt

### Sprint - Curriculum-Katalog v1

- [x] Read-only-Katalog `data/curriculum_catalog_v1.csv` mit Faecher- und Kompetenzeintraegen angelegt
- [x] Kernfaecher Deutsch, Mathematik, EPU, Musik, Kunst, Sport und Sozialkompetenz aufgenommen
- [x] Erweiterte Faecher Ethik, Religion, Werken und Schulgarten aufgenommen
- [x] `EPU` als App-Anzeigename fuer `Epochaler Projektunterricht` modelliert
- [x] Offizielle Quelle fuer EPU als `Heimat- und Sachkunde` dokumentiert
- [x] `Sachunterricht` wird nicht als App-Fach angezeigt
- [x] PySide6-Beobachtungsdialog liest Fach- und Kompetenzlisten aus dem Katalog
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung und keine Datenmodelländerung fuer Beobachtungen umgesetzt
- [x] Keine finale Architekturentscheidung getroffen

### Hotfix - Beobachtungsdialog Kompetenzauswahl lesbarer

- [x] Kompetenzliste zeigt kurze Lernbereich-Labels statt langer Kompetenztexte
- [x] Lange Kompetenztexte bleiben im Katalog und im nicht-persistenten Draft erhalten
- [x] Mehrfachauswahl als sichtbare Checkbox-Liste umgesetzt
- [x] Fachwechsel aktualisiert die Kompetenzliste und setzt die vorherige Auswahl zurueck
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung und keine Datenmodelländerung umgesetzt

### Sprint - Beobachtungsdialog Bewertung pro Kompetenz

- [x] Globale Bewertung aus dem PySide6-Beobachtungsdialog entfernt
- [x] Bewertungs-Auswahl pro ausgewaehlter Kompetenz vorbereitet
- [x] Nicht-persistenter Draft fuehrt Kompetenzbewertungen statt Beobachtungs-Gesamtbewertung
- [x] Abwaehlen einer Kompetenz entfernt deren Bewertung aus dem Draft
- [x] Fachwechsel setzt Kompetenzauswahl und Kompetenzbewertungen zurueck
- [x] Dialoginhalt scrollbar gemacht, damit die Buttonleiste erreichbar bleibt
- [x] Kompetenzauswahl und Bewertungszeilen kompakter gestaltet
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository und keine Datenmodelländerung umgesetzt

### Hotfix - Beobachtungsdialog faecheruebergreifende Kompetenzbewertungen

- [x] Fachwechsel erhaelt bereits ausgewaehlte Kompetenzbewertungen
- [x] Fach-Dropdown als Filter fuer die sichtbare Kompetenzauswahl praezisiert
- [x] Kompetenzen aus mehreren Faechern koennen gleichzeitig im nicht-persistenten Draft stehen
- [x] Kompetenzbewertungszeilen zeigen den Fach-Anzeigenamen und bieten `Entfernen`
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Sprint - PySide6 Stammdaten light

- [x] Navigationseintrag `Stammdaten` ergaenzt
- [x] Stammdaten-light-Seite mit Bereichen fuer Stammgruppen und Kurse ergaenzt
- [x] Hinzufuegen und Umbenennen fuer Stammgruppen und Kurse als nicht-persistenter UI-/Adapter-Draft vorbereitet
- [x] Leere Namen werden mit verstaendlicher Meldung abgelehnt
- [x] Loeschen, Schueler-Umbuchung und produktive Stammgruppen-/Kurspersistenz bewusst nicht umgesetzt
- [x] Keine Beobachtungspersistenz, keine SQLite-Aenderung fuer Beobachtungen, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Sprint - PySide6 Schuelerdialog an Stammdaten anbinden

- [x] PySide6-Dialog `Neuer Schüler` nutzt Stammdaten-light fuer Stammgruppen- und Kursauswahl
- [x] Stammgruppen- und Kursfelder verwenden Dropdowns mit `Bitte auswählen`
- [x] Leerer Name, fehlende Stammgruppe und fehlender Kurs werden vor dem Speichern abgefangen
- [x] Session-lokale Stammdaten sind im Dialog sichtbar, aber nur dauerhaft vorhandene Eintraege koennen fuer `student.create` gespeichert werden
- [x] Keine neue Persistenz, keine Beobachtungspersistenz, keine SQLite-Aenderung, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Hotfix - PySide6 Kursfarben anzeigen

- [x] Kurse im Stammdaten-light-ViewModel um UI-Farbe als Name und Hex-Wert erweitert
- [x] Kursdialoge um feste Farbauswahl fuer Blau, Gruen, Orange, Lila, Rot und Grau erweitert
- [x] Kursfarben in der Stammdaten-Seite als kleiner Farbmarker angezeigt
- [x] Kursfarben in der PySide6-Schuelerliste neben dem Kursnamen angezeigt
- [x] Keine neue Persistenz, keine SQLite-Aenderung, kein ObservationRepository und keine finale Architekturentscheidung umgesetzt

### Sprint - PySide6 UI-Polish

- [x] Dialogbuttons fuer Speichern und Abbrechen vereinheitlicht
- [x] Empty States fuer Schuelerliste und Stammdaten-Seite ergaenzt
- [x] App-Info-Dialog mit Prototyp-Hinweis ergaenzt
- [x] Suchfeld in der Schuelerliste verfeinert
- [x] Einfachen Tastaturkomfort fuer Dialoge vorbereitet
- [x] Keine Fachlogik, keine Persistenz, keine SQLite-Aenderung und keine finale Architekturentscheidung umgesetzt

### Hotfix - macOS-Launcher fuer PySide6-Prototyp

- [x] Doppelklick-faehige Launcher-Datei `launcher/Jenaplan_Kompetenzmanager.command` ergaenzt
- [x] Launcher wechselt robust ins Projektverzeichnis
- [x] Launcher nutzt `.venv/bin/python`, falls vorhanden, sonst `python3`
- [x] README um Terminalstart und Doppelklick-Start ergaenzt
- [x] Kein PyInstaller, kein Installer, kein `.app`-Bundle und keine Packaging-Toolchain umgesetzt
- [x] Keine Fachlogik, keine Persistenz, keine SQLite-Aenderung und keine finale Architekturentscheidung umgesetzt

### Dokumentation - Icon-basierte visuelle Leitlinie

- [x] App-Icon als zentrale gestalterische Referenz dokumentiert
- [x] Farbwelt aus Dunkelblau, Blau, Tuerkis, Gruen, Orange und hellen neutralen Hintergruenden festgehalten
- [x] Weiche Formensprache, Kartenoptik, Weissraum und klare visuelle Hierarchie als UI-Leitlinie ergaenzt
- [x] Leichte moderne Glasoptik als optionales, zurueckhaltendes Stilmittel beschrieben
- [x] Bedeutungsanker Baum, Personen, Diagramm, Kreis/Bogen und farbige Blaetter dokumentiert
- [x] PySide als kuenftige Hauptanwendung dokumentiert
- [x] Keine Codeaenderung, kein Build und kein Commit umgesetzt

### Korrektur-Hotfix - PySide Kursverbuende und Schuelerliste

- [x] Speichern-Buttons in PySide-Dialogen zentral im blauen Primary-Stil dargestellt
- [x] Kursfarben-Palette um Gelb `#EAB308` erweitert
- [x] Schuelerliste wieder mit sauber getrennter Kurs-Spalte hergestellt
- [x] Kursmarker und Kursname in getrenntem Kurs-Zelllayout ohne Ueberlagerung dargestellt
- [x] Session-lokalen Default-Kursverbund `Mathe/Deutsch Kursverbund A` ergaenzt
- [x] Uebersicht `Stammgruppen und Schülerbestand` zeigt Stammgruppen aus dem aktuellen Stammdaten-Scope
- [x] Uebersicht `Stammgruppen und Schülerbestand` zeigt Kurse mit farbigem Marker innerhalb des Kursverbunds
- [x] Kursfilter beruecksichtigt Kurs und Stammgruppen des Kursverbunds
- [x] Offenen UX-Punkt dokumentiert: Kompetenznamen in der Bewertungsliste spaeter eventuell fett darstellen
- [x] Keine neue Persistenz, keine SQLite-Aenderung, kein ObservationRepository, kein Excel-/VBA-Umbau und keine Packaging-Toolchain umgesetzt

### Architektur-Sprint - PySide Hauptanwendung, Excel/VBA Legacy/Export

- [x] Arbeitsbaum vor Sprintbeginn sauber vorgefunden
- [x] ADR-046 ergaenzt: PySide ist Hauptanwendung
- [x] SQLite als produktive lokale Datenbasis dokumentiert
- [x] Excel/VBA auf Export-, Berichts-, Referenz- und Legacy-Kontext zurueckgestuft
- [x] Keine neuen Excel-/VBA-Features, keine VBA-Smoke-Tests und keine VBA-Automation als Zielpfad dokumentiert
- [x] README, PROJECT, ROADMAP, AGENTS und Governance-Dokumente bereinigt
- [x] PySide6-Feasibility als abgeschlossene Machbarkeitsphase markiert
- [x] Backlog um Legacy-Bereinigung, Exportstrategie, Packaging/Installer und SQLite-Ausbau ergaenzt
- [x] Keine Code-Loeschung, keine Produktlogik, keine SQLite-Migration, kein Packaging und kein Commit umgesetzt

### Sprint - PySide Kursverbund bearbeiten

- [x] Arbeitsbaum vor Sprintbeginn sauber vorgefunden
- [x] Kursverbund-Bearbeiten-Dialog fuer Name, Stammgruppen und Kurse ergaenzt
- [x] Stammgruppen und Kurse im Kursverbund per Checkbox auswaehlbar gemacht
- [x] Leerer Name, fehlende Stammgruppe und fehlender Kurs werden verstaendlich abgelehnt
- [x] Kursverbund wird session-lokal im `MasterDataDesktopAdapter` gespeichert
- [x] Stammdaten-Seite zeigt aktualisierte Kursverbund-Auswahl
- [x] Uebersicht nutzt aktualisierte Kurse des Kursverbunds
- [x] Kursfilter bleibt `course_id` plus ausgewaehlte `group_ids`
- [x] Schueleruebersicht mit Kurs-Spalte und farbigem Marker erhalten
- [x] Keine SQLite-Persistenz, keine Migration, kein Repository, kein Excel-/VBA-Umbau und kein Commit umgesetzt

### Nicht Bestandteil

- [x] Keine Beobachtungserfassung
- [x] Keine Schnellbeobachtung oder Gruppenbewertung
- [x] Keine Kompetenzzuordnung in Beobachtungen implementieren
- [x] Kein vollstaendiges Dokumentenmanagement
- [x] Kein Dokument-Upload
- [x] Keine Medienvorschau
- [x] Keine produktive Schueleranlage
- [x] Keine direkte VBA-SQLite-Anbindung
- [x] Keine Berichte
- [x] Keine Kursverwaltung
- [x] Keine Stammgruppenverwaltung
