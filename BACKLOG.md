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
Commit `e96a77e328da98bfb3622201110e6e08c8b3e312`. Der aktuelle HEAD
`926582f7db3a44642b05301fbbb676a91a1f500c` liegt genau einen Commit danach
und korrigiert ausschließlich die individuelle Fachrelevanz der
Dashboard-Heatmap und von `Passende Kinder für diese Stunde`. Dieser Fix ist
umgesetzt, aber unveröffentlicht. Solange `src/version.py` noch Build 400
ausweist, darf daraus kein Artefakt entstehen. Ein Folgebuild benötigt
mindestens Build 401; die sichtbare Version 0.4.0 oder 0.4.1 bleibt PO-offen.

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

## C - Beschlossen und noch umzusetzen

Es gibt weiterhin keine fachliche offene Funktion, die zugleich eindeutig
beschlossen, datenmodellseitig geklärt und als Implementierungssprint
freigegeben ist. Die früher hier geführte deaktivierte Sparkle-2-Updatebasis ist
inzwischen implementiert und deshalb kein C-Punkt mehr. P0-Fehler aus dem
Pilottest werden befundbezogen priorisiert; daraus entsteht keine pauschale
Funktionsfreigabe.

## D - Ideen, noch nicht entschieden

| Idee | Vorläufige Priorität | Entscheidungsbedarf |
| --- | --- | --- |
| Schülerlisten-Import | P1-Kandidat | Formate, Pflichtfelder, Vorschau, Dubletten, Zuordnungen und Atomarität entscheiden. |
| Dublettenprüfung und Wiederholungsimport | P1-Kandidat, Teil des Import-Gates | Identitätsregeln und Konfliktauflösung entscheiden. |
| Weitergehende Archivierung ausgeschiedener Kinder | P2-Kandidat | Der im Schuljahreswechsel umgesetzte schuljahresbezogene Austritt ist von Aufbewahrung und normaler Schülerarchivierung zu trennen. |
| Unterjähriger Mehrkind-/Sammelwechsel | P2-Kandidat | Bleibt getrennt vom umgesetzten jährlichen Schuljahreswechsel und benötigt einen eigenen Lifecycle. |
| Gruppenbeobachtung | P1-Kandidat | Gemeinsames Aggregat gegenüber mehreren Einzelbeobachtungen entscheiden. |
| Schnellbeobachtung mehrerer Kinder | P1-Kandidat | Auswahl, gemeinsamer Kontext und atomare Einzelresultate entscheiden. |
| Gruppenbewertung | P1-Kandidat | Individuelle Bewertung ohne automatische Gleichsetzung entscheiden. |
| Globales `⌘N` für `Neue Beobachtung` | P2-Kandidat | Geltungsbereich, aktiver Kindkontext, Konflikte mit Texteingaben und barrierefreie Alternative entscheiden. |
| `Weitere Beobachtung` nach dem Speichern | P2-Kandidat | Rücksetz-, Vorbelegungs- und Abbruchverhalten entscheiden; kein automatisches Duplizieren. |
| Verbindlicher Initialfokus im Beobachtungsdialog | P2-Kandidat | Zielkontrolle für Neu/Bearbeiten, Tastaturreihenfolge und Screenreader-Verhalten entscheiden. |
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
| Einklappbare Fachbereiche in der Berichtsvorschau | P2-Kandidat | Disclosure-State, Tastaturbedienung, Druck-/PDF-Unabhängigkeit und Verhalten bei langen Berichten entscheiden. |
| Formulierungshilfen für Berichte | P2-Kandidat | Manuelle Verantwortung, Vorlagenumfang und klare Grenze zu KI-/Automatiktext entscheiden. |
| Word-Export | P2-Kandidat | Format, Inhalt, Layout, Historienquelle und Datenschutz entscheiden. |
| Medienvorschau | P2-Kandidat | Dateitypen, sichere Darstellung, Performance und externe Referenzen entscheiden. |
| Stammgruppen archivieren | P2-Kandidat | Historien- und Zuordnungsregeln vor Schreibprozess entscheiden. |
| Kurse archivieren | P2-Kandidat | Historien- und Zuordnungsregeln vor Schreibprozess entscheiden. |
| Automatisierte Backup-Erinnerung | P3-Kandidat | Erinnerung ist kein automatisches Backup; Frequenz und lokale Speicherung entscheiden. |
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

Globales `⌘N`, `Weitere Beobachtung`, Initialfokus, geplante Beobachtungen,
Kompetenzvorlagen, `Zuletzt bearbeitet`, einklappbare Berichtsvorschau,
historische Ansichten, Formulierungshilfen, Medienvorschau, Word-Export und
fachlich geklärte Archivierungsfunktionen.

### P3 - Betrieb und Verteilung

Developer-ID/Notarisierung, Stable-Updateprozess, Diagnosepaket,
Backup-Erinnerung, bewusster Klartextexport finaler RPA-/LCA-Artefakte,
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
