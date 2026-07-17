# Project Constitution

Dieses Dokument legt die verbindlichen Architekturregeln fuer den Jenaplan-Kompetenzmanager ab Sprint 4 fest.

## Source-of-Truth-Regeln

Das Datenmodell ist die einzige fachliche Wahrheit.

Das Design-System ist Source of Truth fuer alle Benutzeroberflaechen.

Die Technical Naming Registry in `docs/TECHNICAL_NAMES.md` ist Source of Truth fuer technische Namen.

Die Data Registry in `docs/DATA_REGISTRY.md` ist Source of Truth fuer SQLite-Datenquellen und historische Workbook-Projektionen.

Das UI Data Mapping in `docs/UI_DATA_MAPPING.md` ist Source of Truth fuer die Herkunft sichtbarer UI-Felder.

Die View Data Ownership in `docs/VIEW_DATA_OWNERSHIP.md` ist Source of Truth fuer Datenverantwortung je Ansicht.

Der Data Lifecycle in `docs/DATA_LIFECYCLE.md` ist Source of Truth fuer freigegebene Schreibprozesse.

## Security-Grenze ab Version 0.2

Sprint 0.2B.4 aktiviert diese Grenze im produktiven Start. Die verbindliche
Reihenfolge lautet: Restore-Worker-Dispatch, Runtime-Pfade, Instanz-Lock,
Restore-Recovery, ausschliesslich technische Runtime-/Security-Pfade,
Security-Store-Pruefung, minimale Authentifizierungsoberflaeche und erst nach
einer erfolgreichen Authentifizierung beziehungsweise vollstaendig
bestaetigten Kontoaufnahme Pilotdaten, Produktverzeichnisse, normales Logging,
fachliche SQLite-Datenbank, Adapter, `AppShell`, Projektionen und Hauptfenster.
Restore-Recovery bleibt damit ausnahmslos vor Login; fachliche Daten werden vor
Authentifizierung weder geoeffnet noch projiziert.

Die Start- und Sperrgrenze ist fail-closed. Marker ohne Store, Store ohne
Marker, korrupte oder neuere unbekannte Security-Daten sowie nicht eindeutig
klassifizierbare Sicherheitsfehler starten keine fachliche App und loesen
weder eine neue Kontoaufnahme noch eine stille Reparatur aus. Genau ein lokales
Konto, eine rein fluechtige In-Memory-Sitzung und eine monotone
`security_epoch` sind verbindlich. Passwortwechsel, Recovery und Support-Reset
invalidieren aeltere Sitzungen. Es gibt keinen allgemeinen Auth-Bypass.

Manuelle Sperre, Inaktivitaet und Wake verdecken nicht transparent, sondern
entfernen alle fachlichen Fenster aus der sichtbaren Oberflaeche. Ungespeicherte
Eingaben bleiben ausschliesslich im Arbeitsspeicher erhalten und werden nach
erfolgreichem Entsperren fortgesetzt. Laufende Backups duerfen im Hintergrund
sicher enden; eine unbestaetigte Restore-Vorschau wird beim Sperren verworfen,
ein bereits bestaetigter Worker-Handoff nicht abgebrochen. Eine Sitzung wird
niemals ueber einen Neustart oder Restore hinweg fortgesetzt.

Die lokale Anwendungssperre schuetzt ausschliesslich den normalen Zugang ueber
die Anwendung. Sie ist keine Verschluesselung der Datenbank, Dokumente oder
Backups. `kompetenzmanager.sqlite`, verwaltete Dokumente und `.jkmbackup`
bleiben unverschluesselt; FileVault, ein geschuetztes Betriebssystemkonto und
sichere Geraeteverwaltung bleiben notwendig.

Sprint 0.2C.1 darf nach erfolgreicher Authentifizierung und nach Aufbau der
fachlichen Shell einmalig `Erste Schritte` anzeigen. Diese Ansicht ist
ausschliesslich Orientierung und Navigation. Sie darf keine fachlichen Daten
anlegen, keinen Import starten, kein Backup automatisch erzeugen, keine
fachliche Entscheidung treffen und keine Security-/Restore-Reihenfolge
veraendern. Der lokale Fortschritt gehoert zu `app-preferences.json`, nicht zum
Security Store, nicht zur fachlichen SQLite-Datenbank und nicht zu
`.jkmbackup`.

Authentifizierungsdaten sind technisch und fachlich vollstaendig von allen
Schueler-, Beobachtungs-, Kompetenz-, Berichts-, LEG- und Dokumentdaten
getrennt. Der kanonische Security Store liegt unter
`<runtime-root>/security/security.sqlite`, besitzt eine eigene Versionierung
und ist niemals Bestandteil von Backup, Restore, Export oder Diagnose. Ein
Restore fachlicher Daten ersetzt, loescht oder initialisiert ihn nicht.

Version 0.2 erlaubt genau ein aktives lokales Lehrkraftkonto je Installation.
Es gibt kein Masterkennwort, keinen Pepper im App-Bundle, kein Cloudkonto,
keinen Cloud-Reset, keine Rollen und keinen Mehrbenutzerbetrieb. Passwortverlust
darf fachliche Daten weder loeschen noch unbrauchbar machen. Der Security Core
bleibt eine eigenstaendige Domain-/Application-/Infrastructure-Grenze; Qt,
fachliche Adapter und Widgets greifen nicht direkt auf den Store zu.

Sprint 0.2B.2 stellt ausschliesslich diesen Core bereit. Eine spaetere
Startintegration muss Neuinstallation und ungeschuetzte Bestandsinstallation
bewusst unterscheiden. Sie darf erst nach eigener Freigabe die App sperren;
der produktive Start bleibt in diesem Sprint unveraendert und unblocked.

Sprint 0.2B.3 erlaubt ausschliesslich einen Qt-freien Offline-Support-Reset mit
Ed25519. Es gibt weiterhin kein Masterkennwort. Private Schluessel duerfen
niemals im Repository, Build oder App-Bundle liegen; die App enthaelt nur eine
oeffentliche Key-Registry, deren Rotation und Widerruf ein App-Update erfordert.
Anfrage und Token muessen kurzlebig, einmalig und vollstaendig an Installation,
Nutzer, Anfrage, Nonce, Aktion und `key_id` gebunden sein. Das Offline-Verfahren
besitzt ein dokumentiertes Risiko durch eine falsch gesetzte lokale Uhr.

Vor jeder Reset-Transaktion ist ein mit dem vorhandenen Backupformat
erfolgreich erzeugtes und vollstaendig verifiziertes fachliches
Sicherheitsbackup zwingend. Der Security Store bleibt ausgeschlossen. Der
Reset darf ausschliesslich Authentifizierungszustaende auf
`password_reset_pending` setzen, Recovery-Zustaende widerrufen und die monotone
Security-Epoch erhoehen. Fachliche Daten, Dokumente, Backups, IDs und
Restore-Vertraege duerfen nicht veraendert werden. UI, Startintegration,
Sitzung, neues Passwort und neue Recovery-Codes bleiben ausserhalb von 0.2B.3.

## Architekturprinzipien

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

SQLite ist die produktive lokale Datenbasis.

Python verantwortet Datenmodell, Application Layer, Domain Layer, Persistenz, UI-nahe Adapter, ViewModels, PySide-Oberflaeche, UI-Projektionen, Berichte, Exporte und Fachlogik.

Excel/openpyxl ist aus dem aktiven Projektpfad entfernt und nur noch im archivierten Legacy-Bereich `legacy/excel/` zulaessig, wenn ein ausdruecklicher Legacy- oder Exportauftrag vorliegt.

VBA ist kein Zielpfad fuer neue Features, UI, Smoke-Tests, Automatisierung oder produktive Workflows.

Alte VBA-Quellen, Seeds und Workbook-Generatoren bleiben unter `legacy/excel/` als Legacy-Altstand versioniert, werden aber nicht zur Hauptanwendung ausgebaut.

Fachliche Eingaben erfolgen nicht direkt in fachlichen Tabellen.

Primaeres Eingabe-Pattern sind PySide-Dialoge und PySide-Screens, die freigegebene Adapter, Commands, Services und Repositories nutzen.

VBA-UserForms und worksheet-basierte Dialogseiten sind historische Artefakte der Excel-Linie und werden fuer neue Entwicklung nicht weiterverfolgt.

Vor der technischen Umsetzung eines neuen Eingabedialogs muss ein UX-Prototyp als verbindliche visuelle Referenz erstellt, mit Laura bzw. dem Product Owner reviewed und freigegeben werden.

Der verbindliche Ablauf fuer neue Eingabedialoge lautet:

1. UX-Prototyp erstellen
2. UX-Review mit Laura bzw. Product Owner durchfuehren
3. UX-Freigabe dokumentieren
4. PySide-Dialog oder PySide-Screen moeglichst 1:1 nach dem freigegebenen UX-Prototyp umsetzen
5. Validierung, Adapter-Anbindung und fachliche Logik erst danach ergaenzen

Der UX-Prototyp ist keine technische Implementierung. Er ist die visuelle Referenz fuer den spaeteren PySide-Dialog oder Screen.

Designentscheidungen fuer Eingabedialoge werden im UX-Prototyp getroffen, nicht frei in Legacy-Excel-/VBA-Artefakten.

PySide-Dialoge duerfen:

- Eingaben sammeln
- einfache Pflichtfeld- und Formatpruefungen fuer unmittelbare Benutzerfuehrung durchfuehren
- technische IDs aus Auswahlfeldern uebergeben
- freigegebene Services aufrufen
- nach erfolgreichem Speichern die betroffene Ansicht aktualisieren

PySide-Dialoge duerfen nicht:

- fachliche Logik enthalten
- direkt in fachliche Tabellen oder SQLite schreiben
- Datenmodellentscheidungen treffen
- eigene Schattenhaltung erzeugen
- UI-Positionen als technische Identitaet verwenden

Nach erfolgreichem Speichern wird die Dialogseite verlassen und die aufrufende oder betroffene Ansicht wird aus dem Datenmodell aktualisiert.

## Legacy Runtime Adapter und Export Refresh

Der folgende Excel/VBA-Runtime-Adapter ist ein historischer, nicht weiter verfolgter Pfad der Excel-Linie.

Der damalige freigegebene Pfad lautete:

```text
Worksheet-Dialogseite
-> VBA Adapter
-> Python CLI/Bridge
-> ApplicationCommandDispatcher
-> Command
-> Service
-> Repository
-> SQLite
```

VBA las in diesem Legacy-Pfad Eingaben ausschliesslich ueber registrierte Named Ranges.

VBA enthaelt keine Fachlogik, erzeugt keine fachlichen IDs, validiert keine Fachregeln und schreibt nicht direkt in SQLite.

Nach erfolgreichem Python Command erzeugt Python ein Projection-Refresh-Paket.

VBA darf ausschliesslich diesen Projection Output in registrierte Projektionsbereiche der geoeffneten Arbeitsmappe kopieren.

VBA darf die Projektion nicht selbst berechnen, sortieren oder fachlich interpretieren.

SQLite bleibt fachliche Source of Truth.

Der Projection Builder bleibt Eigentuemer der Projektion.

UI ist immer Projektion und niemals fachliche Datenquelle.

UI darf anzeigen, filtern, sortieren und navigieren.

UI darf fachliche Daten nur ueber definierte Schreibprozesse veraendern.

Darstellungsregeln wie Sortierung, Gruppierung und Filterung gehoeren ausschliesslich zur UI-Projektion.

Sie veraendern niemals die zugrunde liegenden fachlichen Entitaeten.

Die Datenhaltung bleibt unabhaengig von der Darstellung.

Excel-/Workbook-Projektionen sind historisch archiviert. Neue Exportprojektionen brauchen eine eigene fachliche Freigabe und duerfen die PySide-/SQLite-Schichten nicht umgehen.

Excel darf diese Projektion anzeigen und technische Zellbezuege aufloesen, ist aber keine Haupt-UI.

Excel darf die fachliche Reihenfolge der Projektion nicht durch dynamische Sortier- oder Filtermechanismen veraendern.

Hilfstabellen, Formeln, Named Ranges, Shapes und sichtbare Zellen duerfen das Datenmodell nicht umgehen.

Auswertungen duerfen keine eigenen Schatteninformationen erzeugen.

## PySide-Hauptanwendung und Excel-Projektion

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Excel/VBA bleibt unter `legacy/excel/` als historischer Altstand erhalten, ist aber nicht mehr die Zielrichtung fuer die Haupt-App.

Der validierte Spike-Pfad lautet:

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Auch fuer PySide6 gilt:

- keine Businesslogik in der GUI
- keine fachliche ID-Erzeugung in der GUI
- keine direkten SQLite-Schreibzugriffe aus Widgets
- keine Umgehung von Dispatcher, Service, Validator oder Repository

Excel/VBA bleibt im Legacy-Archiv erhalten. Excel ist kein aktiver Standardpfad.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut. Der Ruecksprungpunkt fuer den Excel-/xlwings-Pfad ist `checkpoint-excel-adapter-before-python-gui`.

Offen bleiben produktiver Nutzer-Datenbankpfad, Backup/Restore, Packaging als macOS-App, Updates/Migrationen und spaetere Exportformate.

## Architecture Baseline v3.0

Architecture Baseline v3.0 ist die verbindliche Schichtenbaseline nach der PySide-Architekturentscheidung.

```text
Adapter Layer
-> Application Layer
-> Domain Layer
-> Infrastructure Layer
-> Projection Layer
-> PySide UI / freigegebene Exportprojektion
```

Verantwortlichkeiten:

- Adapter Layer: nimmt Interaktionen entgegen und baut Commands; keine Fachlogik.
- Application Layer: Commands, Dispatcher und Routing; keine Fachlogik, kein SQL, keine Excel-Logik.
- Domain Layer: Services, Validatoren und fachliche Regeln.
- Infrastructure Layer: Repositories, SQLite und Persistenz.
- Projection Layer: PySide ViewModels, UI-nahe Anzeigeprojektionen und explizit freigegebene Export Builder.
- PySide UI: Hauptanwendung fuer Anzeige, Navigation, Dialoge und Benutzerinteraktion.
- Excel UI: historischer Legacy-Altstand unter `legacy/excel/`.

Standard-Datenfluss:

```text
User
-> PySide-Dialog oder freigegebener Adapter
-> Adapter
-> Dispatcher
-> Command
-> Service
-> Repository
-> SQLite
-> ViewModel / Query-Projektion
-> PySide-Ansicht oder freigegebene Exportprojektion
```

SQLite ist die produktive lokale Source of Truth fuer fachliche Daten.

Python ist die einzige fachliche Schreibschicht.

VBA enthaelt keine Businesslogik und schreibt nicht direkt in SQLite.

PySide ist Haupt-UI, aber nicht fachliche Datenquelle.

Excel bleibt historischer Altstand, nicht fachliche Datenquelle.

Neue Funktionen entstehen nach dem Standardablauf:

1. vorhandene Daten ergaenzen
2. Registry kennt die Datenquelle
3. PySide ViewModel oder freigegebene Exportprojektion aktualisieren
4. UI zeigt die Projektion
5. PySide navigiert ueber technische IDs; Export-/Legacy-Projektionen duerfen technische IDs abbilden

Neue Funktionen duerfen nur entstehen durch:

- bestehende Daten erweitern
- registrierte neue Datenquelle ergaenzen
- ViewModel oder freigegebenen Export Builder erweitern
- UI-Projektion ergaenzen
- PySide-Navigation ergaenzen; Legacy-/Export-Navigation nur bei ausdruecklichem Auftrag

Nicht erlaubt sind:

- eigene Schattenlogik
- lokale Zwischendatenhaltung
- doppelte Speicherung derselben Information

## Entity first

Neue Funktionen werden kuenftig nicht zuerst als Maske gedacht, sondern als fachliche Entitaet.

Nicht:

```text
Wir brauchen eine Kompetenzverwaltung.
```

Sondern:

```text
Welche Entitaet entsteht oder wird erweitert? Competency.
```

Die verbindliche Reihenfolge lautet:

```text
Entity
-> Validator
-> Repository
-> Service
-> Application Command Layer
-> Builder
-> UI
-> Navigation
```

Das Schema selbst wird nicht als Python-Klasse implementiert.

Die fachliche Definition einer Entity erfolgt ausschliesslich ueber die Architektur-Dokumentation und die Workbook Data Registry.

Validator pruefen fachliche Eingaben.

Repositories lesen und schreiben Datenquellen.

Services koordinieren fachliche Prozesse.

Der Application Command Layer nimmt technische Commands von Adaptern entgegen und delegiert an Services.

Command Adapter wie CLI oder spaeter VBA duerfen keine Fachlogik enthalten.

Builder erzeugen Projektionen.

UI zeigt Projektionen und ruft keine Repositories direkt auf.

Navigation erfolgt ausschliesslich ueber technische IDs.

## Entity / Storage / Projection

Entity ist das fachliche Objekt, zum Beispiel Student, Group, Course, Competency oder Observation.

Storage ist die physische Ablage im Workbook, zum Beispiel `data_students` mit `tbl_students`.

Projection ist die sichtbare oder auswertbare Darstellung, zum Beispiel Schuelerkarte, Schuelerprofil, Dashboard oder Bericht.

Regeln:

- Entities bleiben stabil.
- Storage kann sich technisch kontrolliert aendern.
- Projections koennen sich gestalterisch aendern.
- Projektionen duerfen keine fachliche Wahrheit speichern.

## Builder-Schicht

Der Builder ist eine eigene Architekturschicht zwischen Daten und Workbook/UI.

```text
Data
-> Builder
-> Workbook/UI
-> VBA-Interaktion
```

Der Builder erzeugt:

- Hidden Data Sheets
- Excel-Tabellen
- Named Ranges
- UI-Projektionen
- vorbereitete Navigationspunkte

Der Builder veraendert keine fachlichen Entitaeten.

Der Builder erzeugt ausschliesslich Workbook-Struktur und Projektionen.

Builder duerfen Projektionen aus mehreren registrierten Datenquellen erzeugen, sofern diese Datenquellen in `docs/DATA_REGISTRY.md`, `docs/VIEW_DATA_OWNERSHIP.md` und `docs/UI_DATA_MAPPING.md` fuer die jeweilige Projektion freigegeben sind.

Fuer Schuelerprojektionen duerfen mindestens gelesen werden:

- `tbl_students`
- `tbl_groups`
- `tbl_courses`

Diese Tabellen werden dabei ausschliesslich gelesen.

Gruppen- oder Kursinformationen duerfen nicht redundant in `tbl_students` uebernommen werden.

Der Builder enthaelt keine spontane Fachlogik ausserhalb der Data Registry.

Fachliche Ableitungen muessen aus registrierten Datenquellen und dokumentierten Regeln entstehen.

## Backlog-relevante Architekturanforderungen

Die Architektur muss folgende spaetere Anforderungen tragen, ohne erneut grundsaetzlich umgebaut zu werden:

- Schuelerverwaltung: anlegen, aendern, archivieren; keine Loeschung; `student_id` bleibt stabil.
- Stammgruppenverwaltung: anlegen, aendern, archivieren; `group_id` bleibt stabil.
- Kursverwaltung: Kurs 1/2/3, Farbe aus `data_courses`; `course_id` bleibt stabil.
- Kursuebersicht: liest Schueler aus mehreren Stammgruppen und zeigt Stammgruppe auf Schuelerkarten.
- Beobachtungserfassung: `observation_id`, Bezug zu `student_id`, Mehrfachbezug zu Kompetenzen.
- Kompetenz-/Lehrplanpflege: `competency_id`, Faecherbezug, Hierarchie, Historisierung offen.
- Dokumente und Medienanhaenge: Dateien werden referenziert, studentenzentriert abgelegt und nicht in Excel eingebettet.
- Automatisch zusammengestellte Vorbereitungsinformationen fuer Lernentwicklungsgespraeche und Berichte bleiben abgeleitete Auswertungsprojektionen. Sie schreiben keine Kompetenz-, Beobachtungs- oder Bewertungsdaten.
- Sprint 7G.1 fuehrt nach Product-Owner- und Datenmodellfreigabe einen eigenen persistenten LEG-Arbeitsentwurf fuer manuelle Vorbereitung, bewusste Referenzauswahl und gemeinsam festgehaltene Inhalte ein. Ein LEG bleibt fachlich von einem Bericht getrennt und ist weder finale Version noch Archiv.
- Dashboards bleiben reine Lese-/Auswertungsschicht. Ein freigegebener Bericht ist langfristig ein versionierter, eingefrorener fachlicher Ausgabestand; die laufende Berichtsvorbereitung bleibt davon getrennt.
- Historisierung: offene Entscheidung vor produktiver Beobachtungserfassung.

## Identitaet

Sichtbare Namen sind niemals technische Identitaeten.

Technische Identitaet erfolgt ausschliesslich ueber IDs.

Namen, Ueberschriften, Zellpositionen, Blattpositionen und sichtbare Texte duerfen nicht als technische Identitaet verwendet werden.

Navigation erfolgt immer ueber technische IDs:

- `student_id`
- `group_id`
- `course_id`
- `competency_id`
- `observation_id`
- weitere registrierte IDs

## Datenhaltung

Es gibt keine doppelte Datenhaltung.

Workbook-Datenquellen werden ausschliesslich in der Workbook Data Registry definiert.

Neue Datenquellen duerfen nicht ohne Erweiterung von `docs/DATA_REGISTRY.md` eingefuehrt werden.

UI-Projektionen duerfen nur aus registrierten Datenquellen entstehen.

Neue Funktionen erweitern vorhandene Daten, statt eigene Dateninseln zu erzeugen.

Keine Funktion erzeugt Schattenlogik.

Erweiterbarkeit ist wichtiger als kurzfristige Implementierung.

Sichtbare Begriffe duerfen sich aendern. Technische Namen bleiben stabil.

## View Ownership

Jede Ansicht besitzt genau definierte Datenquellen.

Eine Ansicht darf nur Datenquellen lesen und schreiben, die in `docs/VIEW_DATA_OWNERSHIP.md` fuer diese Ansicht freigegeben sind.

Neue Ansichten duerfen nicht ohne View Data Ownership umgesetzt werden.

Neue Datenquellen duerfen in einer Ansicht erst verwendet werden, nachdem `docs/VIEW_DATA_OWNERSHIP.md` entsprechend erweitert wurde.

Dashboards und Live-Berichtsvorbereitungen lesen Daten, schreiben aber niemals fachliche Daten. Das spaetere Erstellen, Pruefen, Freigeben oder Korrigieren eines Berichtstands ist ein eigener fachlicher Schreibprozess und braucht vor der Umsetzung Datenmodell-, Lifecycle- und Product-Owner-Freigabe.

## Verbindliche Implementierungsreihenfolge

Eine neue Funktion wird kuenftig in dieser Reihenfolge entwickelt:

1. `docs/PROJECT_CONSTITUTION.md` pruefen
2. `docs/TECHNICAL_NAMES.md` pruefen
3. `docs/DATA_REGISTRY.md` erweitern
4. `docs/DATA_LIFECYCLE.md` ergaenzen
5. `docs/VIEW_DATA_OWNERSHIP.md` ergaenzen
6. `docs/UI_DATA_MAPPING.md` ergaenzen
7. erst danach implementieren

Diese Reihenfolge ist verbindlich.

## Schreibprozesse

Fachliche Daten duerfen nur ueber freigegebene Schreibprozesse veraendert werden.

Kein Schreibprozess darf ohne Eintrag in `docs/DATA_LIFECYCLE.md` umgesetzt werden.

Archivieren ist der Standard fuer fachliche Deaktivierung. Physische Loeschung ist nicht vorgesehen, solange kein eigener fachlicher Entscheid vorliegt.

Schreibprozesse muessen transaktional gedacht werden: Sie erfolgen vollstaendig oder gar nicht.

Keine halben Datensaetze sind erlaubt.

Beispiel Schueler anlegen:

1. `student_id` erzeugt
2. `data_students` geschrieben
3. `group_id` und `course_id` gueltig
4. Projektionen koennen daraus gelesen werden

Wenn ein Schritt fehlschlaegt, darf kein inkonsistenter Zwischenzustand entstehen.

Dateien werden nicht in Excel eingebettet.

Excel speichert fuer Dokumente und Medien ausschliesslich registrierte Referenzen.

Physische Dateien liegen im Dateisystem.

Dokumente gehoeren immer zu einem Schueler.

Beobachtungsanhaenge liegen ebenfalls unter dem Schueler, koennen aber zusaetzlich einen Beobachtungsbezug besitzen.

Beobachtungen duerfen nicht durch eingebettete Dateien oder unkontrollierte Anlagen belastet werden.

## Navigation

Navigation erfolgt immer ueber technische IDs.

Nicht erlaubt ist Navigation ueber:

- Namen
- Zellpositionen
- Blattpositionen
- sichtbare Texte

Ein oeffentlicher VBA-Einstiegspunkt darf keinen impliziten Zustand voraussetzen. Er muss benoetigte Objekte selbst sicher ermitteln oder eine verstaendliche Fehlermeldung ausgeben.

## Technische Namen

Technische Namen muessen in `docs/TECHNICAL_NAMES.md` registriert sein.

Neue technische Namen duerfen nicht kreativ lokal erfunden werden.

Technische Namen sind ASCII-kompatibel, ohne Umlaute und ohne Leerzeichen.

Sichtbare deutsche UI-Begriffe duerfen nicht als technische Schluessel verwendet werden.

Bestehende technische Namen werden nicht ohne eigenen Migrationssprint umbenannt.

## UI

Alle UI-Elemente folgen `docs/DESIGN_SYSTEM.md`.

Neue UI-Felder duerfen erst umgesetzt werden, wenn ihre Datenherkunft in `docs/UI_DATA_MAPPING.md` dokumentiert ist.

Normale Entwicklungssprints veraendern das freigegebene Design nicht.

## Verbotene Umgehungen

Nicht erlaubt sind:

- UI-Tabellen als fachliche Datenquelle
- UI-Zellen als technische Identitaet
- VBA als Ort fuer Fachlogik
- Auswertungen mit eigener Schattenlogik
- neue Datenquellen ohne `DATA_REGISTRY.md`
- neue technische Namen ohne `TECHNICAL_NAMES.md`
- neue Ansichten ohne `VIEW_DATA_OWNERSHIP.md`
- neue UI-Felder ohne `UI_DATA_MAPPING.md`
- Schreibprozesse ohne `DATA_LIFECYCLE.md`
- Navigation ueber Namen statt IDs
- doppelte Datenhaltung fuer dieselbe fachliche Information
- Designaenderungen ohne eigenen UX-Sprint
