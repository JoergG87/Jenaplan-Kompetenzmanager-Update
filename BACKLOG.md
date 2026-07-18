# Product Backlog

## Zweck und Statuslogik

Dieses Backlog gleicht den Produktstand nach Version 0.2 mit dem tatsächlich
implementierten PySide6-/SQLite-Pfad ab. Ein Eintrag bedeutet nur dann eine
Freigabe, wenn er in Kategorie C steht und zusätzlich als Sprint in
`SPRINTS.md` freigegeben ist.

Jeder Funktionspunkt steht genau in einer der folgenden Kategorien:

- A: umgesetzt und bestätigt
- B: umgesetzt, aber im Pilottest fachlich oder ergonomisch zu prüfen
- C: beschlossen und noch umzusetzen
- D: Idee, noch nicht entschieden
- E: langfristige Option
- F: verworfen oder durch neue Architektur ersetzt
- G: unklar beziehungsweise widersprüchlich

Pilottestbefunde, Wünsche und Produktentscheidungen werden getrennt erfasst.
Keine Projektion darf automatische Benotung oder automatische
Leistungsbewertung einführen.

## A - Umgesetzt und bestätigt

| Funktionspunkt | Bestätigter Stand 0.2 |
| --- | --- |
| Lehrplankatalog | Lehrplanbasierter, historienfähiger Kompetenzkatalog ist produktiv in SQLite angebunden. |
| Produktive SQLite-Persistenz | Stammdaten, Beobachtungen, Bestätigungen, Dokumentreferenzen, Stundenplan, Bericht und LEG nutzen den produktiven lokalen Datenpfad. |
| Einzelbeobachtung | Anlegen, Bearbeiten und Soft Delete mit Datum, Kontext, Notiz und Einzelbewertungen sind umgesetzt. |
| Schnellbeobachtung für genau ein Kind | Beobachtung ohne Kompetenzzuordnung ist mit verpflichtender Notiz umgesetzt; dies ist keine Mehrkind-Schnellbeobachtung. |
| Zentraler Beobachtungsdialog | PySide-Arbeitsdialog mit Fach, Kontext, Kompetenzen, Einzelbewertungen, Notiz und Anhängen ist umgesetzt. |
| Kompetenzzuordnung | Eine Beobachtung kann mehrere Kompetenzen auch fachübergreifend mit jeweils eigener Bewertung referenzieren. |
| Beobachtungsverlauf | Profilkarten, Detailansicht, Suche, Fach-/Bewertungsfilter, Ein-/Ausklappen und Evidenznavigation sind umgesetzt. |
| Fachübergreifende Beobachtungen | Anzeige `Fächerübergreifend` bei Erhalt der einzelnen Fachlabels ist umgesetzt. |
| Aktuellen Kompetenzstand bestätigen | Speichern und manuelles Anpassen eines aktuellen bestätigten Stands sind umgesetzt. |
| Kompetenzübersichten | Fach, Kompetenzbereich, Thema, Kompetenz, aktueller bestätigter Stand, Vorschlag und Evidenz sind getrennt projiziert. |
| Schüler anlegen, bearbeiten und archivieren | Produktive SQLite-Schreibprozesse sind umgesetzt; es gibt keine physische Löschung. |
| Stammgruppen | Anlegen und Umbenennen sowie Nutzung in Stammdaten, Schülerlisten und Stundenplan sind umgesetzt. |
| Kurse | Anlegen und Bearbeiten einschließlich Farbe sowie Nutzung in Stammdaten, Schülerlisten und Stundenplan sind umgesetzt. |
| Kursverbünde | Anlegen und Bearbeiten mit Stammgruppen-/Kursrelationen ist umgesetzt. |
| Kursübersicht | Schüler eines Kurses sind im lokalen Arbeitsbereich `Schüler > Kurse` erreichbar. |
| Stundenplan | Persistente Wochenplanung für Stammgruppe, Kurs und Kursverbund ist umgesetzt. |
| `Für diese Stunde` | Aktuelle beziehungsweise nächste Stunde und fachbezogene passende Kinder werden im Dashboard projiziert. |
| Dashboard-Navigation | Direkte Wege zu Stammgruppe, Kurs oder Kursverbund und in den bestehenden Beobachtungsdialog sind umgesetzt. |
| Mini-Heatmap Stammgruppe mal Fach | Neutrale Dokumentationsabdeckung ohne Leistungswerte ist umgesetzt. |
| Berichtsentwürfe | Persistente, bearbeitbare und live-referenzierende Entwürfe mit frei gesetztem Zeitraum sind umgesetzt. |
| Mehrere Berichtszeiträume | Getrennte Entwürfe können unterschiedliche explizite Zeiträume tragen; verbindliche Berichtstypen bleiben G. |
| Berichtrevisionen | Unveränderliche, hashverifizierte Revisionen und historische Leseansicht sind umgesetzt. |
| Finales Berichts-PDF | Bewusste manuelle Erzeugung eines unveränderlichen Artefakts aus der aktuellen verifizierten Revision ist umgesetzt. |
| LEG-Revisionen | Abschluss, Folgerevisionen und historische schreibgeschützte Ansichten sind umgesetzt. |
| Erneutes finales LEG-PDF | Für die jeweils aktuelle abgeschlossene Revision kann ein unveränderliches PDF-Artefakt erzeugt werden. |
| Dokumentablage | Studentenzentrierte verwaltete Dateien und externe Referenzen mit Metadaten sind umgesetzt. |
| Dokumenttypen | Der definierte MVP-Typbestand ist umgesetzt. |
| Datei öffnen | Dokumente können über den Betriebssystempfad geöffnet werden. |
| Anhänge bei Beobachtungen | Hinzufügen, Anzeigen und Entfernen im Beobachtungsprozess sind umgesetzt. |
| Profilanzeige für Dokumente | Dateien und Beobachtungsanhänge sind im Schülerprofil sichtbar. |
| Verwaltete Dateien im Backup | Registrierte verwaltete Dokumente und finale Bericht-/LEG-Artefakte sind Bestandteil des verifizierten Backupvertrags. |
| Lokales Konto und Passwortschutz | Ein lokales Lehrkraftkonto mit Argon2id, Drosselung und flüchtiger Sitzung ist umgesetzt. |
| Recovery-Codes | Erzeugen, einmaliges Anzeigen, Verbrauchen und Erneuern sind umgesetzt. |
| Technischer Support-Reset-Workflow | Anfrage, Offline-Tokenprüfung, Sicherheitsbackup und Resetabschluss sind umgesetzt; Produktivschlüssel bleibt D. |
| macOS-Pilotpaket | Reproduzierbarer arm64-App-/DMG-/Dokumentbau mit ad-hoc Signierung ist umgesetzt. |

## B - Im Pilottest zu validieren

Diese Funktionen sind umgesetzt. Die Prüfung entscheidet über Befunde, nicht
automatisch über eine Funktionsänderung.

| Validierungspunkt | Zu prüfender Stand |
| --- | --- |
| Echter Sleep/Wake | Sperrt und entsperrt der reale Pilot-Mac zuverlässig, ohne ungespeicherte Eingaben zu verlieren? |
| Physische Touch-ID-Nutzung | Erscheint die echte Systemaufforderung und bleibt Passwort immer als verständlicher Fallback verfügbar? |
| App-Switcher bei Sperre | Bleiben fachliche Inhalte in der gesperrten Anwendung ausreichend verdeckt? |
| Gespeicherte Geräteanmeldung | Sind Aktivierung, Startverhalten, Widerruf und Fehlerrückfall verständlich und sicher? |
| Backup/Restore unter realer Nutzung | Sind Erstellen, Prüfen, Vorschau, bewusste Bestätigung, Neustart und wiederhergestellte verwaltete Dateien alltagstauglich? |
| LEG-Arbeitsentwurf, Vorschau und Gesprächsführung | Sind der umgesetzte sechsphasige Arbeitsraum, Vorschau und Gesprächsführung während der Bearbeitung sichtbar und erreichbar? |
| Berichtsvorschau und Exporttext | Sind Struktur, Belegdichte, Kopieren und Textdatei-Export für Lauras Weiterarbeit hilfreich? |
| Dokumentationsstatus | Ist die Anzeige verständlich und neutral statt kontrollierend? |
| `Noch nicht dokumentiert` | Unterstützt der Hinweis die Planung, ohne Defizit oder Bewertung zu behaupten? |
| Schülerprofil | Ist der Überblick ruhig, verständlich und im Alltag schneller als die Detailreiter allein? |
| Lernentwicklung im Schülerprofil | Bleiben aktuelle und historische Entwicklung ausschließlich aus belegten Beobachtungen und Bestätigungen verständlich? |
| Kompetenzstand-Vorschläge | Sind Berechnung, bestätigter Stand und Evidenz klar getrennt; ist `Vorschlag` die richtige Bezeichnung? |
| Pädagogische Hinweise | Sind `Stärken` und `Im Blick behalten` aus vorhandener Evidenz hilfreich, ohne automatische Bewertung zu suggerieren? |
| Dokumente und Medien | Sind Typen, Profilanzeige, Anhänge und `Datei öffnen` ausreichend; wird der Beobachtungsdialog zu dicht? |
| Dashboard | Sind stundenbezogene Information, Mini-Heatmap und passende Kinder in ihrer Dichte hilfreich? |
| Beobachtungsbasierter Alltagsworkflow | Sind Einzel-/Schnellbeobachtung, Kompetenzwahl, Bewertungsdarstellung einschließlich der typografischen Hervorhebung von Kompetenznamen und Rückwege schnell genug? |
| `Erste Schritte` | Unterstützt der geführte Einstieg die reale Einrichtung, ohne als Pflichtassistent zu wirken? |

## C - Beschlossen und noch umzusetzen

Derzeit gibt es keine fachliche offene Funktion, die zugleich eindeutig
beschlossen, datenmodellseitig geklärt und als Implementierungssprint
freigegeben ist. P0-Fehler aus dem Pilottest werden befundbezogen priorisiert,
sind aber keine vorab definierte neue Funktion.

## D - Ideen, noch nicht entschieden

| Idee | Vorläufige Priorität | Entscheidungsbedarf |
| --- | --- | --- |
| Schülerlisten-Import | P1-Kandidat | Formate, Pflichtfelder, Vorschau, Dubletten, Zuordnungen und Atomarität entscheiden. |
| Dublettenprüfung und Wiederholungsimport | P1-Kandidat, Teil des Import-Gates | Identitätsregeln und Konfliktauflösung entscheiden. |
| Schuljahreswechsel | P1-Kandidat nach Import | Historie, Versetzung, Archivierung, Übernahme, Backup und Rollback entscheiden. |
| Versetzung | P1-Kandidat nach Schuljahreswechsel | Klassenstufe, Zielgruppe, Sonderfälle und historische Zugehörigkeit entscheiden. |
| Archivierung ausgeschiedener Kinder | P1-Kandidat nach Schuljahreswechsel | Regel für Austritt gegenüber normaler Schülerarchivierung entscheiden. |
| Kurs-/Gruppenübernahme in ein neues Schuljahr | P1-Kandidat nach Schuljahreswechsel | Kopieren, Weiterführen und historische Zuordnung entscheiden. |
| Gruppenbeobachtung | P1-Kandidat | Gemeinsames Aggregat gegenüber mehreren Einzelbeobachtungen entscheiden. |
| Schnellbeobachtung mehrerer Kinder | P1-Kandidat | Auswahl, gemeinsamer Kontext und atomare Einzelresultate entscheiden. |
| Gruppenbewertung | P1-Kandidat | Individuelle Bewertung ohne automatische Gleichsetzung entscheiden. |
| Klassenmatrix | P1/P2-Kandidat | Fachlicher Zweck nach Pilottest des Dokumentationsstatus entscheiden. |
| Kursmatrix | P1/P2-Kandidat | Abgrenzung zur vorhandenen Kursübersicht und Datenaggregation entscheiden. |
| Gruppenbezogene Dokumentationsstände für Kurs/Kursverbund | P2-Kandidat | Die vorhandene Stammgruppen-Heatmap nicht unbemerkt verallgemeinern. |
| Geplante Beobachtungen | P2-Kandidat | Eigene Entität, Fälligkeit, Abschluss und Verwerfen entscheiden. |
| Nächster Beobachtungsanlass | P2-Kandidat nach geplanten Beobachtungen | Keine automatische pädagogische Priorisierung einführen. |
| Kompetenzvorlagen für Unterrichtssituationen | P2-Kandidat | Lokale Vorlage, Katalogbezug und Übernahmeverhalten entscheiden. |
| Historie bestätigter Kompetenzstände | P2-Kandidat | Aktuelles Upsert-Modell gegenüber unveränderlicher Historie entscheiden. |
| Kommentare zu Kompetenzständen | P2-Kandidat | Das vorhandene persistente Notizfeld besitzt noch keinen freigegebenen UI-/Historienvertrag. |
| Erweiterte historische Entwicklungen | P2-Kandidat | Nur belegte Ereignisse, keine erfundenen Zwischenwerte oder Trendnoten. |
| Zusätzliche Ansichten auf Beobachtungsverläufe | P2-Kandidat | Nutzen und Abgrenzung zu vorhandener Suche, Filtern und Kompetenz-Evidenz entscheiden. |
| Historische Trends außerhalb des Schülerprofils | P2-Kandidat | Eigene Auswertungsfläche statt allgemeiner Dashboardanalyse entscheiden. |
| Formulierungshilfen für Berichte | P2-Kandidat | Manuelle Verantwortung, Vorlagenumfang und klare Grenze zu KI-/Automatiktext entscheiden. |
| Word-Export | P2-Kandidat | Format, Inhalt, Layout, Historienquelle und Datenschutz entscheiden. |
| Medienvorschau | P2-Kandidat | Dateitypen, sichere Darstellung, Performance und externe Referenzen entscheiden. |
| Stammgruppen archivieren | P2-Kandidat | Historien- und Zuordnungsregeln vor Schreibprozess entscheiden. |
| Kurse archivieren | P2-Kandidat | Historien- und Zuordnungsregeln vor Schreibprozess entscheiden. |
| Automatisierte Backup-Erinnerung | P3-Kandidat | Erinnerung ist kein automatisches Backup; Frequenz und lokale Speicherung entscheiden. |
| Produktiver Support-Reset-Schlüssel und Supportprozess | P3-Kandidat | Schlüsselverwaltung, Rotation, Identitätsprüfung und Betrieb freigeben. |
| Developer-ID-Signierung und Apple-Notarisierung | P3-Kandidat | Zertifikat, Verantwortlichkeit und reproduzierbaren Releaseprozess klären. |
| Update- und Migrationsmechanismus | P3-Kandidat | Paketverteilung, Datenbankkompatibilität, Rollback und Signierung entscheiden. |
| Diagnosepaket | P3-Kandidat | Strikte Datenschutz-Allowlist und Security-Ausschlüsse entscheiden. |
| Geregelter Geräte- oder Schulwechsel | P3-Kandidat | Backup/Restore, externe Referenzen, Security-Neuanlage und Übergabeprozess entscheiden. |
| Weitere Datei-/Ausgabeformate | P2/P3-Kandidat | Finales PDF ist umgesetzt; zusätzliche Formate einzeln entscheiden. |

## E - Langfristige Optionen

| Option | Einordnung |
| --- | --- |
| Windows-Build | Eigenes Plattform-, Packaging-, Test- und Supportvorhaben. |
| Windows Hello/Credential Manager | Erst nach Windows-Produktentscheidung; keine Dummy-Sicherheit. |
| Verschlüsselung | Separate Bedrohungs-, Schlüssel-, Backup-, Restore- und Recoveryarchitektur erforderlich. |
| Mehrbenutzerbetrieb | Eigenes Konto-, Besitz-, Konflikt- und Auditmodell erforderlich. |
| Rollen und Berechtigungen | Nicht aus dem lokalen Ein-Konto-Modell ableiten; eigener fachlicher Vertrag nötig. |
| Cloud-/Mehrgerätebetrieb | Eigenes Datenschutz-, Synchronisations-, Konflikt- und Betriebsmodell erforderlich. |
| Schulweite Installation | Benötigt Verteilung, Betrieb, Support, Rollen und Datenschutzentscheidungen. |

## F - Verworfen oder durch neue Architektur ersetzt

| Historischer Punkt | Einordnung |
| --- | --- |
| Excel/VBA als Hauptanwendung | Durch PySide6/SQLite und ADR-046 ersetzt. |
| Excel-Feature-1-UX-Review und Ausbau `Neuer Schüler` | Der produktive PySide-Schülerdialog ersetzt diesen historischen Vorbereitungsweg. |
| VBA-UserForm `frm_student_new` | Deprecated; keine aktive Umsetzung. |
| Worksheet-Dialogseite `dlg_neuer_schueler` | Historischer UX-/Legacy-Pfad, nicht produktiver Eingabepfad. |
| CLI-/Python-Bridge für Excel-Schreibprozesse | Für die Hauptanwendung durch direkte PySide-Adapter-/Application-Pfade ersetzt. |
| Command Queue und Projection Refresh der geöffneten Arbeitsmappe | Für die Hauptanwendung durch den PySide-/SQLite-Pfad ersetzt. |
| Aktive Excel-/VBA-Build- und AppleScript-Smoke-Aufgaben | Unter `legacy/excel/` historisch archiviert; keine Pflichtchecks. |
| Legacy-Excel-Code später prüfen und archivieren | Erledigt: Die Altlinie ist unter `legacy/excel/` eingeordnet und aus dem aktiven Produktpfad entfernt. |
| PySide6-Migration als Zukunftsarbeit | Abgeschlossen; PySide6 ist die Hauptanwendung. |
| Allgemeine Idee `Entwicklung sichtbar` auf dem Dashboard | Verworfen; Dashboard bleibt stundenbezogener Arbeitsstart. |
| Automatische Benotung oder automatische Leistungsbewertung | Pädagogisch und produktseitig ausgeschlossen. |

## G - Unklar oder widersprüchlich

| Punkt | Klärung |
| --- | --- |
| `Automatisches finales PDF` | Finale Bericht-/LEG-PDFs sind bewusst manuell aus verifizierten Revisionen erzeugbar. Ob `automatisch` nur reproduzierbare Erzeugung oder Erzeugung beim Finalisieren meint, ist nicht entschieden. |
| Kursverbünde löschen/archivieren und Schüler umbuchen | Persistentes Anlegen/Bearbeiten ist umgesetzt; Lösch-, Archivierungs- und Umbuchungsregeln sind fachlich offen. |
| Verbindliche Berichtstypen und Berichtszeiträume | Freie explizite Zeiträume funktionieren; der verbindliche schulische Umfang ist in ADR-050 weiterhin PO-offen. |
| Bericht-/LEG-Freigaberollen und Aufbewahrung | Revisionen sind technisch umgesetzt; Rollen, Aufbewahrung, Zugriffsschutz und Archivierung sind weiterhin offen. |
| Eine Gruppenbeobachtung oder mehrere Einzelbeobachtungen | Der alte Begriff beschreibt zwei unterschiedliche Datenmodelle; vor Entscheidung nicht als ein Feature behandeln. |

## Priorisierung nach dem Pilottest

### P0 - Pilotkritische Fehler

- Datenverlust oder nicht reproduzierbar fehlerhafte Speicherung
- Sicherheitsfehler oder unzulässige Freigabe fachlicher Inhalte
- blockierte Hauptabläufe
- starke UI-Überlagerungen oder abgeschnittene Kernaktionen

### P1 - Nächster alltagsrelevanter Funktionsschnitt

1. Schülerlisten-Import als Discovery-/Architecture-Gate: höchste erwartete
   Zeitersparnis bei Ersteinrichtung, aber relevante Identitäts- und
   Transaktionsrisiken.
2. Schuljahreswechsel erst nach Import- und Historienentscheidung: hoher
   jährlicher Nutzen, zugleich größtes Migrations- und Rollbackrisiko.
3. Gruppenbeobachtung beziehungsweise Mehrkind-Schnellbeobachtung nach
   Pilotmessung des täglichen Beobachtungswegs: potenziell häufigster Nutzen,
   aber ungeklärtes Beobachtungsaggregat und Datenschutz.
4. Klassen-/Kursmatrix nach Validierung der vorhandenen
   Dokumentationsprojektionen: hoher Überblicksnutzen, aber kein Ersatz für
   Einzelbeobachtung und keine automatische Bewertung.

Die vorhandene Dashboard-Navigation ist umgesetzt und daher kein P1-Punkt.

### P2 - Fachliche Komfortfunktionen

Geplante Beobachtungen, Kompetenzvorlagen, historische Ansichten,
Formulierungshilfen, Medienvorschau, Word-Export und fachlich geklärte
Archivierungsfunktionen.

### P3 - Betrieb und Verteilung

Produktiver Support-Reset, Developer-ID/Notarisierung, Updateprozess,
Diagnosepaket, Backup-Erinnerung, Gerätewechsel und später Windows.

### P4 - Strategische Erweiterungen

Verschlüsselung, Mehrbenutzerbetrieb, Rollen, Cloud-/Mehrgerätebetrieb und
schulweite Installation.

## Abhängigkeiten der wichtigsten Planungskandidaten

### Schülerlisten-Import - Status D, P1-Kandidat

- Fachlicher Nutzen: reduziert wiederkehrende manuelle Anlage und Tippfehler.
- Vorentscheidungen: CSV/XLSX oder weitere Formate, Pflichtfelder, Vorschau,
  Zuordnung, Fehlerprotokoll und bewusste Bestätigung.
- Datenmodell: Identitäts- und Dublettenregeln für bestehende und archivierte
  Kinder; keine Umgehung stabiler IDs.
- Pilottest: tatsächlichen Einrichtungsaufwand und reale Listenformate erheben.
- Datenschutz: lokale Verarbeitung, keine ungeprüften temporären Klartextreste.
- Migrationsrisiko: Wiederholungsimport darf keine Duplikate, Teilbestände oder
  unerwartete Reaktivierung erzeugen.
- Tests: Parsergrenzen, Vorschau, Dubletten, ungültige Zeilen, atomarer
  Gesamtrollback, Wiederholungsimport, Archivfälle und UI-Adaptergrenze.
- Kleinster Sprint: erst Discovery-/Architecture-Gate; danach gegebenenfalls
  Parser und read-only Vorschau, noch ohne Schreiben.
- Akzeptanzrahmen: kein Teilimport; vor Schreiben vollständige Vorschau; bei
  einem Fehler unveränderter Datenbestand; Archivierung statt Löschung.

### Schuljahreswechsel - Status D, P1-Kandidat nach Import

- Fachlicher Nutzen: sichere jährliche Versetzung und Weiterführung der
  Schulorganisation bei unveränderter Historie.
- Vorentscheidungen: neues Schuljahr, Klassenstufen, Versetzungsregeln,
  Gruppen-/Kursübernahme, Austritte und Archivierung.
- Datenmodell: Zeitgeltung von Zugehörigkeiten und Schuljahr ist derzeit nicht
  als freigegebener Wechselvertrag modelliert.
- Pilottest: reale Jahreswechselabläufe, Ausnahmen und benötigte Vorschau
  erheben.
- Datenschutz: ausgeschiedene Kinder und Aufbewahrungsfristen klären.
- Migrationsrisiko: hoch; historische Beobachtungen, Berichte, LEG und IDs
  dürfen nicht umgedeutet werden.
- Tests: Sicherheitsbackup, vollständige Vorschau, atomarer Wechsel,
  Fehlerrollback, Wiederholung, Historienleseansichten und Archivfälle.
- Kleinster Sprint: Product Discovery und Datenmodell-/Lifecycle-Entscheidung;
  keine gemeinsame Implementierung mit dem ersten Import-Sprint.
- Akzeptanzrahmen: Sicherheitsbackup vor Schreiben, explizite Bestätigung,
  vollständige Historie und beweisbarer Rollback.

### Gruppenbeobachtung / Mehrkind-Schnellbeobachtung - Status D, P1-Kandidat

- Fachlicher Nutzen: reduziert Dialogwechsel in häufigen Unterrichtssituationen.
- Vorentscheidungen: gemeinsame Beobachtung oder mehrere Einzelbeobachtungen,
  gemeinsame Notiz, individuelle Bewertungen, Schülerauswahl und
  Stammgruppen-/Kurs-/Kursverbundkontext.
- Datenmodell: das aktuelle Beobachtungsmodell ist kindbezogen; keine neue
  Mehrkind-Relation ohne ausdrückliche Entscheidung.
- Pilottest: Zeitbedarf und typische Gruppengröße im echten Workflow messen.
- Datenschutz: keine unbeabsichtigte Offenlegung fremder Kinddaten in Auswahl,
  Fehlern oder späterer Bearbeitung.
- Migrationsrisiko: bestehende Einzelbeobachtungen bleiben unverändert; neue
  Semantik darf Historie und Berichte nicht umdeuten.
- Tests: individuelle Bewertung, atomare Speicherung, vollständiger Rollback,
  spätere Einzelbearbeitung, Soft Delete, Referenzvalidierung und Tastaturweg.
- Kleinster Sprint: Product Discovery plus Datenmodell-/Architekturentscheidung;
  danach gegebenenfalls Mehrkind-Auswahl mit reinem Draftzustand.
- Akzeptanzrahmen: keine Teilgruppe bei Fehler, keine globale Gruppenwertung,
  jede resultierende Kind-Evidenz bleibt nachvollziehbar.

## Historische Backlog-Hinweise

Die früheren Überschriften und Ideen bleiben in den Kategorien A bis G
inhaltlich erhalten. Es wurden keine Ideen wegen fehlender Priorität gelöscht.
Excel-/VBA-Punkte wurden in F verschoben, bereits umgesetzte PySide-/SQLite-
Punkte in A oder B. Da der frühere Backlog keine stabilen Backlog-IDs führte,
konnten keine IDs übernommen werden.
