# Product Backlog

## Zweck und Statuslogik

Dieses Backlog gleicht den Produktstand mit der veröffentlichten Basis 0.4.0 /
Build 400 und dem aktuellen unveröffentlichten Quellstand ab. Ein Eintrag
bedeutet nur dann eine Freigabe, wenn er in Kategorie C steht und zusätzlich
als Sprint in `SPRINTS.md` freigegeben ist.

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

## Release-Baseline und Statusstichtag

Der veröffentlichte, unveränderliche Pilotstand 0.4.0 / Build 400 stammt aus
Commit `e96a77e328da98bfb3622201110e6e08c8b3e312`. Der erste Produktfix danach,
`926582f7db3a44642b05301fbbb676a91a1f500c`, korrigiert die individuelle Fachrelevanz der
Dashboard-Heatmap und von `Passende Kinder für diese Stunde`. Dieser Fix ist
umgesetzt, aber unveröffentlicht. Für die am 08.09.2026 beauftragte lokale
Paketierung ist 0.4.1 / Build 401 als neue Identität festgelegt. Fertigstellung
und Paketprüfung ergeben sich erst aus dem neuen Manifest; Build 400 bleibt
unverändert.

## A - Umgesetzt und bestätigt

| Funktionspunkt | Bestätigter Stand bis Build 400 |
| --- | --- |
| Lehrplankatalog | Lehrplanbasierter, historienfähiger Kompetenzkatalog ist produktiv in SQLite angebunden. |
| Produktive SQLite-Persistenz | Stammdaten, Beobachtungen, Bestätigungen, Dokumentreferenzen, Stundenplan, Bericht und LEG nutzen den produktiven lokalen Datenpfad. |
| Einzelbeobachtung | Anlegen, Bearbeiten und Soft Delete mit Datum, Kontext, Notiz und Einzelbewertungen sind umgesetzt. |
| Schnellbeobachtung für genau ein Kind | Beobachtung ohne Kompetenzzuordnung ist mit verpflichtender Notiz umgesetzt; dies ist keine Mehrkind-Schnellbeobachtung. |
| Zentraler Beobachtungsdialog | PySide-Arbeitsdialog mit Fach, Kontext, Kompetenzen, Einzelbewertungen, Notiz und Anhängen ist umgesetzt. |
| Beobachtungskontext `Partnerarbeit` | Ist als auswählbarer, speicher- und wieder ladbarer Beobachtungskontext umgesetzt. |
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
| Stammgruppe in kombinierten Schülerlisten | Kurs-, Kursverbund- und Gesamtschülerlisten zeigen die Stammgruppe sichtbar; nur ein eindeutiger Ein-Gruppen-Kontext blendet die redundante Spalte aus. |
| Stundenplan | Persistente Wochenplanung für Stammgruppe, Kurs und Kursverbund ist umgesetzt. |
| `Für diese Stunde` | Aktuelle beziehungsweise nächste Stunde und fachbezogene passende Kinder werden im Dashboard projiziert. |
| Dashboard-Navigation | Direkte Wege zu Stammgruppe, Kurs oder Kursverbund sind umgesetzt. `Passende Kinder` öffnet das Schülerprofil über die stabile `student_id`; `Beobachten` bleibt eine getrennte Aktion. |
| Mini-Heatmap Stammgruppe mal Fach | Neutrale Dokumentationsabdeckung ohne Leistungswerte ist umgesetzt. |
| Fachillustrationen/Fachvignetten | Dekorative, an stabile Fach-IDs gebundene Motive sind im Dashboard umgesetzt; sie erzeugen keine Fach- oder Bewertungslogik. |
| Schuljahreswechsel | Vorschau, individuelle und gebündelte Planauflösung, Passwort-Step-up, verifiziertes Pflichtbackup, Maintenance-Gate, atomare Aktivierung, Rollback, Integritätsprüfung und Übergangshistorie sind Bestandteil von Build 400. |
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
| Beaufsichtigte macOS-Pilotupdatebasis | Sparkle-Bridge, Application-Port, Settings-Projektion, Pilotkanal und monotone Buildlogik sind umgesetzt; daraus folgt keine Stable-, Appcast- oder Folgereleasefreigabe. |
| Lokales Konto und Passwortschutz | Ein lokales Lehrkraftkonto mit Argon2id, Drosselung und flüchtiger Sitzung ist umgesetzt. |
| Recovery-Codes | Erzeugen, einmaliges Anzeigen, Verbrauchen und Erneuern sind umgesetzt. |
| Technischer Support-Reset-Workflow | Anfrage, Offline-Tokenprüfung, Sicherheitsbackup und Resetabschluss sind umgesetzt; der bestätigte öffentliche Produktivschlüssel ist ab `0.2.2` aktiv. |
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
| Schuljahreswechsel unter realen Pilotbedingungen | Ist der vollständig implementierte Build-400-Ablauf mit Vorschau, Zuordnung, Pflichtbackup, Passwort-Step-up, Aktivierung und Ergebnisdarstellung im realen Jahreswechsel verständlich und betrieblich belastbar? |
| Sicherer In-App-PDF-Viewer | Sind der gemeinsame read-only Viewer sowie der Qt-/HTML-Zugang zu finalen RPA-/LCA-Artefakten im realen Vergleich verständlich und alltagstauglich? |
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
| Beaufsichtigte Pilotupdates | Sind reale Updateprüfung, Aufschub, Rückfall und die Trennung von Pilot, Appcast und Stable im vorgesehenen Betrieb verständlich und sicher? |
| `Erste Schritte` | Unterstützt der geführte Einstieg die reale Einrichtung, ohne als Pflichtassistent zu wirken? |

### Fünf neue Komfortfunktionen im unveröffentlichten Quellstand

| Funktion | Nachweis und verbleibende Alltagsprüfung |
| --- | --- |
| `⌘N` für neue Beobachtung | `7dc1b3c`; Profil, selektierte Schülerzeile und Suche sichtbar geprüft; reale Unterrichtsbedienung noch auswerten. |
| `Speichern & weitere` | `a094a69`; zwei getrennte Einträge, Fehlererhalt und Abbruch des Folgeentwurfs geprüft; fortlaufende Erfassung im Alltag prüfen. |
| Verlässlicher Initialfokus | `22edc03`; Neu, Schnellbeobachtung und Bearbeiten sichtbar geprüft. |
| Einklappbare Berichtsfächer | `b58568e`; Tastatur, Klappzustand und unverändertes Exportmodell geprüft; längere reale Berichte im Alltag prüfen. |
| Dezenter Sicherungshinweis | `4e6a142`; unbekannt, fehlend, aktuell und alt geprüft; synthetische UI-Abnahme ersetzt keine Cipher-/Bundle-Abnahme. |

## C - Beschlossen und noch umzusetzen

Die fünf am 07.09.2026 freigegebenen Komfortfunktionen sind implementiert
und einzeln nach automatisierter und sichtbarer synthetischer Prüfung
committet. Sie stehen jetzt in Kategorie B für die Nutzung durch Laura.
Die Importvorbereitung ist abgeschlossen; der eigentliche Import verbleibt
in Kategorie D. Es ist kein weiterer Implementierungssprint eröffnet.

## D - Ideen, noch nicht entschieden

| Idee | Vorläufige Priorität | Entscheidungsbedarf |
| --- | --- | --- |
| Schülerlisten-Import | P1-Kandidat | Discovery unten abgeschlossen; Erstimportumfang und Wiederholungsidentität vor Implementierung entscheiden. |
| Dublettenprüfung und Wiederholungsimport | P1-Kandidat, Teil des Import-Gates | Identitätsregeln und Konfliktauflösung entscheiden. |
| Weitergehende Archivierung ausgeschiedener Kinder | P2-Kandidat | Der im Schuljahreswechsel umgesetzte schuljahresbezogene Austritt ist von Aufbewahrung und normaler Schülerarchivierung zu trennen. |
| Unterjähriger Mehrkind-/Sammelwechsel | P2-Kandidat | Bleibt getrennt vom umgesetzten jährlichen Schuljahreswechsel und benötigt einen eigenen Lifecycle. |
| Gruppenbeobachtung | P1-Kandidat | Gemeinsames Aggregat gegenüber mehreren Einzelbeobachtungen entscheiden. |
| Schnellbeobachtung mehrerer Kinder | P1-Kandidat | Auswahl, gemeinsamer Kontext und atomare Einzelresultate entscheiden. |
| Gruppenbewertung | P1-Kandidat | Individuelle Bewertung ohne automatische Gleichsetzung entscheiden. |
| Klassenmatrix | P1/P2-Kandidat | Fachlicher Zweck nach Pilottest des Dokumentationsstatus entscheiden. |
| Kursmatrix | P1/P2-Kandidat | Abgrenzung zur vorhandenen Kursübersicht und Datenaggregation entscheiden. |
| Gruppenbezogene Dokumentationsstände für Kurs/Kursverbund | P2-Kandidat | Die vorhandene Stammgruppen-Heatmap nicht unbemerkt verallgemeinern. |
| `Zuletzt bearbeitet` auf `Heute` | P2-Kandidat | Quelle, Zeitraum, Sortierung und neutrale Darstellung ohne Kontroll- oder Prioritätsaussage entscheiden. |
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
| Bewusster Klartextexport finaler RPA-/LCA-Artefakte | P2/P3-Kandidat | Zielwahl, No-Clobber, Integritätsprüfung, Warnung und Verantwortung für die bewusst unverschlüsselte Ausgabedatei entscheiden; der sichere Viewer bleibt unverändert. |
| Developer-ID-Signierung und Apple-Notarisierung | P3-Kandidat | Zertifikat, Verantwortlichkeit und reproduzierbaren Releaseprozess klären. |
| Schemaändernde Update-Migrationen | P3-Kandidat | Vor der ersten Schemaänderung Vorwärtsmigration, Sicherung, Wiederanlauf, Kompatibilitätsfenster und Downgradeverbot gesondert entscheiden. |
| Diagnosepaket | P3-Kandidat | Strikte Datenschutz-Allowlist und Security-Ausschlüsse entscheiden. |
| Geregelter Geräte- oder Schulwechsel | P3-Kandidat | Backup/Restore, externe Referenzen, Security-Neuanlage und Übergabeprozess entscheiden. |
| Weitere Datei-/Ausgabeformate | P2/P3-Kandidat | Finales PDF ist umgesetzt; zusätzliche Formate einzeln entscheiden. |

## E - Langfristige Optionen

| Option | Einordnung |
| --- | --- |
| Windows-Build | Eigenes Plattform-, Packaging-, Test- und Supportvorhaben. |
| Windows Hello/Credential Manager | Erst nach Windows-Produktentscheidung; keine Dummy-Sicherheit. |
| Portable beziehungsweise zentrale Schlüsselwiederherstellung | Die lokale Final-V4-Verschlüsselung ist umgesetzt; Gerätewechsel, zentrale Schlüsselverwaltung und DMK-Recovery benötigen eigene Bedrohungs-, Betriebs- und Recoveryarchitektur. |
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
2. Gruppenbeobachtung beziehungsweise Mehrkind-Schnellbeobachtung nach
   Pilotmessung des täglichen Beobachtungswegs: potenziell häufigster Nutzen,
   aber ungeklärtes Beobachtungsaggregat und Datenschutz.
3. Klassen-/Kursmatrix nach Validierung der vorhandenen
   Dokumentationsprojektionen: hoher Überblicksnutzen, aber kein Ersatz für
   Einzelbeobachtung und keine automatische Bewertung.

Der Schuljahreswechsel und die vorhandene Dashboard-Navigation sind umgesetzt
und daher keine P1-Punkte.

### P2 - Fachliche Komfortfunktionen

Die am 07.09.2026 freigegebenen Funktionen stehen in Kategorie C.
Weitere Kandidaten bleiben geplante Beobachtungen,
Kompetenzvorlagen, `Zuletzt bearbeitet`,
historische Ansichten, Formulierungshilfen, Medienvorschau, Word-Export und
fachlich geklärte Archivierungsfunktionen.

### P3 - Betrieb und Verteilung

Developer-ID/Notarisierung, Stable-Updateprozess, Diagnosepaket,
bewusster Klartextexport finaler RPA-/LCA-Artefakte,
Gerätewechsel und später Windows. Der produktive
Support-Reset-Schlüssel und der beaufsichtigte Pilot-Updateprozess sind mit
`0.2.2` umgesetzt und bleiben im realen Pilottest zu validieren.

### P4 - Strategische Erweiterungen

Portable Schlüsselwiederherstellung, Mehrbenutzerbetrieb, Rollen,
Cloud-/Mehrgerätebetrieb und schulweite Installation.

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

Die früheren Ideen bleiben grundsätzlich in den Kategorien A bis G inhaltlich
nachvollziehbar. Umgesetzte Punkte werden aus D entfernt und in A oder B
geführt; deshalb steht der Schuljahreswechsel nicht länger als Zukunftsidee im
Backlog. Excel-/VBA-Punkte wurden in F verschoben. Da der frühere Backlog keine
stabilen Backlog-IDs führte, konnten keine IDs übernommen werden.

## Schülerlisten-Import – vorbereitete Produktentscheidung vom 07.09.2026

**Ziel und beobachteter Bestand:** Mehrere Kinder mit vorhandenen Stammgruppen
und Kursen einrichten. `students` enthält `student_id`, Vor-/Nachname, Notiz,
Aktivstatus und Zeitstempel; weder Geburtsdatum noch externe Schul-ID.
Zuordnungen liegen ausschließlich in `student_school_year_assignments` mit
Schuljahr und Gültigkeitsintervall. Grundlage dieses Reviews sind
`src/core/final_v4_schema.py`, `StudentDesktopAdapter.save_new_student` und
`CreateStudentWithInitialEnrollment` in `src/application/school_year_assignment.py`.

**Empfohlener kleiner Erstumfang (noch nicht implementiert):** Nur neue Kinder
anlegen; bekannte Kinder bewusst überspringen. Keine automatische Korrektur,
Reaktivierung, Archivierung, Gruppen-/Kursanlage oder Umzuordnung. Import nur
ins aktuelle Schuljahr, gültig ab dem bewusst angezeigten heutigen Datum bis
Schuljahresende. Liegt heute außerhalb des aktuellen Schuljahrs, ist der
Import gesperrt. Andere Eintrittsdaten wären eine eigene Produktentscheidung.

| Bereich | Konkreter Vorschlag |
| --- | --- |
| Datei | Lokale UTF-8-CSV, BOM zulässig, ausdrücklich gewähltes Komma oder Semikolon. Kein Excel-/VBA-Laufzeitpfad. Obergrenze zunächst 1 MiB und 1.000 Datenzeilen; größere oder fehlerhaft dekodierte Dateien werden vor der Vorschau abgelehnt. |
| Pflichtfelder | Sichtbare Spalten `Vorname` und `Nachname`; beide nach Entfernen äußerer Leerzeichen gefüllt. CSV-Anführungszeichen, Umlaute und Zeilenumbrüche in korrekt zitierten Zellen sauber parsen. Formeln niemals ausführen; Dateiinhalt ist ausschließlich Text. |
| Optionale Identität | `Schüler-ID` darf ausschließlich eine schon bekannte interne `student_id` nennen. Unbekannte angegebene IDs sind ein Konflikt; neue interne IDs erzeugt die Anwendung. Keine heimliche externe ID-Zuordnung. |
| Zuordnung | Vorhandene Stammgruppe und Kurs für den Import bewusst wählen; Vorschau zeigt pro Zeile die stabile Zuordnung. Abweichende Zeilen können ausdrücklich vorhandenen Zielen zugeordnet werden. Freitext erzeugt keine Gruppen/Kurse. |
| Vorschau | Dateizeile, Vor-/Nachname, geplante Gruppe/Kurs, Aktion `Neu anlegen` oder `Überspringen`, verständlicher Fehler. Zusammenfassung nennt Anzahl, Schuljahr und Gültigkeitsbeginn. Keine Speicherung beim Öffnen oder Navigieren. |
| Dubletten | Doppelte interne ID oder identische Eingabezeilen blockieren bis zur ausdrücklichen Auflösung. Normalisierte Namen dienen nur als Warnsignal. Gleichnamige Kinder sind zulässig; niemals automatisch zusammenführen. Treffer auch unter archivierten Kindern anzeigen und bewusst überspringen oder als anderes Kind anlegen lassen. |
| Wiederholung | Bekannte ID mit passenden Stammdaten kann ausdrücklich übersprungen werden; widersprüchliche Namen sind zu klären. Ohne stabile ID sind Namensgleichheit und bereits importiert fachlich nicht unterscheidbar. Eine vollautomatische wiederholbare Synchronisation ist deshalb nicht Bestandteil dieses Erstumfangs. |
| Datenschutz | Quelle nur lokal lesen; keine vollständige Dateikopie, Kindernamen oder Notizen in Logs. Vorschau und Quellinhalt beim Schließen verwerfen. Keine externe Übertragung. |

**Atomarität und Architektur:** Der existierende Einzelanlage-Service beginnt
für jedes Kind eine eigene `BEGIN IMMEDIATE`-Transaktion. Eine Schleife über
`save_new_student` wäre daher kein atomarer Import. Ein späterer Batch muss
im Application Layer genau eine keyed Verbindung und eine Transaktion für
sämtliche bestätigten Neuanlagen und Erstzuordnungen besitzen. Gemeinsame
Validierungen und Repositories sollen auf derselben Verbindung wiederverwendet
werden; Widgets enthalten weder SQL noch Identitätsentscheidungen.

Unmittelbar vor dem Schreiben müssen Root-/Session-/Maintenance-Schutz,
aktuelles Schuljahr, Gruppen-/Kursbeziehungen, bekannte Identitäten und der
bestätigte Vorschauplan erneut geprüft werden. Der freigegebene Plan bezieht
sich auf die bereits gelesenen Bytes; keine unbemerkte erneute Dateiübernahme.
Ändert sich eine relevante Zuordnung zwischen Vorschau und Commit, wird die
Ausführung abgelehnt und eine neue Vorschau verlangt. Bei jedem Fehler wird
alles zurückgerollt; Erfolg bedeutet alle ausdrücklich gewählten Neuanlagen.
Ein zweiter Klick während der Ausführung darf keinen zweiten Batch starten.

**Abnahmefälle für die spätere Implementierung:** UTF-8/BOM, Umlaute und
CSV-Quoting; leere Namen, fehlende/mehrfache Spalten und Grenzen; identische
Zeilen, gleichnamige Kinder, bekannte/falsche/archivierte IDs; fehlendes oder
inzwischen gewechseltes Schuljahr; ungültige Gruppen-/Kursrelation; Abbruch
vor dem Commit; Fehler nach der ersten von mehreren Neuanlagen mit null
persistierten Änderungen; erneuter Klick und Wiederholung einer Datei;
Cocoa-Vorschau mit Tastatur und vollständig sichtbarer Fehlermeldung.

**Entscheidungsvorlage:** Der obige lokale Erstimport kann ohne Schemaänderung
umgesetzt werden, sobald dieser konkrete Umfang freigegeben ist. Für einen
verlässlichen automatischen Wiederholungsimport muss zuvor geklärt werden,
welche stabile ID die tatsächliche Schulquelle liefert. Eine neue externe
ID oder Zuordnungstabelle wäre eine Datenmodelländerung und erfordert die
vorgeschriebene Rücksprache. Es wurden weder Importcode noch Tabellen,
UI-Felder oder zukünftige technische Namen als aktive Verträge angelegt.
