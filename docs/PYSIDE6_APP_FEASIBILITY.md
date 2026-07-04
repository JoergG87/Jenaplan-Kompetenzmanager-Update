# PySide6 App Feasibility

Dieses Dokument dokumentiert die abgeschlossene Machbarkeitspruefung, aus der die PySide-Hauptanwendung hervorgegangen ist.

Status: Historische Umsetzungspruefung, erfolgreich abgeschlossen.

Hinweis: Die offene Architekturfrage wurde nach Freigabe des App-Icons und weiteren PySide-Sprints entschieden. PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers. SQLite ist die produktive lokale Datenbasis. Excel/VBA bleibt als Export-, Berichts-, Referenz- oder Legacy-Projektion erhalten.

## 1. Ausgangslage

Der Jenaplan-Kompetenzmanager besitzt inzwischen eine validierte Python-Schichtenarchitektur:

```text
Adapter Layer
-> Application Layer
-> Domain Layer
-> Infrastructure Layer
-> Projection Layer
-> Excel UI / Export
```

SQLite ist fuer `student.create` die fachliche Source of Truth.

Python bleibt die einzige fachliche Schreibschicht.

Adapter duerfen Interaktionen entgegennehmen, Eingaben sammeln, Commands erzeugen und den `ApplicationCommandDispatcher` aufrufen.

Adapter duerfen keine Businesslogik enthalten, keine fachlichen IDs erzeugen und nicht direkt in SQLite schreiben.

Excel/VBA bleibt unter `legacy/excel/` archiviert. Excel ist kein aktiver Standardpfad mehr.

Der Excel/VBA-Runtime-Adapter wird vorerst nicht weiter ausgebaut. Der Ruecksprungpunkt fuer den Excel-/xlwings-Pfad ist `checkpoint-excel-adapter-before-python-gui`.

Entschieden ist:

- PySide6 ist Hauptanwendung
- SQLite ist produktive lokale Datenbasis
- Excel ist nur noch archivierter Legacy-Altstand; spaetere Exporte brauchen eigene Freigabe
- VBA wird nicht fuer neue Features, UI, Smoke-Tests oder produktive Workflows weiterverfolgt

## 2. Validierter Spike

Der PySide6-Spike wurde manuell validiert.

Nachgewiesener Pfad:

```text
PySide6 GUI
-> Desktop Adapter
-> ApplicationCommandDispatcher
-> CreateStudentCommand
-> StudentService
-> SQLiteStudentRepository
-> SQLite
```

Validierter Stand:

- App startet.
- Maske `Neuer Schüler` funktioniert.
- Ein Schuelerdatensatz wurde in SQLite geschrieben.
- Speichern laeuft ueber Application, Service und Repository.
- Qt Widgets schreiben nicht direkt in SQLite.
- Tests: `python3 -m pytest` mit 26 bestandenen Tests.
- Historischer Build: `python3 build.py` war im Spike erfolgreich; der Build ist heute archiviert und kein Standardcheck mehr.
- Commit: `5363e18`
- Tag: `spike-pyside6-student-create`

Bewertung:

Der Spike beweist, dass PySide6 als Adapter technisch in die bestehende Architektur passt.

Diese Machbarkeitsphase ist durch ADR-046 abgeschlossen. PySide ist die Hauptanwendung.

## 3. Moegliche Zielarchitektur

Eine moegliche PySide6-Struktur sollte die bestehende Architektur respektieren und GUI-Code von fachlicher Logik trennen.

Vorgeschlagene Struktur:

```text
src/desktop_app/
    main.py
    app.py
    shell.py
    navigation.py
    screens/
        dashboard_screen.py
        student_list_screen.py
        student_profile_screen.py
        observation_placeholder_screen.py
        reports_screen.py
        settings_screen.py
    dialogs/
        new_student_dialog.py
    adapters/
        student_desktop_adapter.py
        group_desktop_adapter.py
        course_desktop_adapter.py
    view_models/
        student_view_model.py
        group_view_model.py
        course_view_model.py
```

Rollen:

- `main.py`: Startpunkt, erzeugt `QApplication`.
- `app.py`: initialisiert Hauptfenster und globale Abhaengigkeiten.
- `shell.py`: App-Rahmen mit Navigation, Titelbereich und Inhaltsbereich.
- `navigation.py`: zentrale Navigation zwischen Screens, keine Fachlogik.
- `screens/`: reine Anzeige- und Interaktionsflaechen.
- `dialogs/`: modale Dialoge fuer Eingaben.
- `adapters/`: GUI-nahe Adapter zur Application-Schicht.
- `view_models/`: Anzeige-DTOs, Sortier- und Formatierungsdaten fuer Views.

Regeln:

- Widgets enthalten keine Businesslogik.
- Widgets enthalten keine SQL-Queries.
- Widgets schreiben nicht direkt in SQLite.
- Adapter duerfen Commands erzeugen und den Dispatcher aufrufen.
- Repositories kapseln SQLite.
- Services und Validatoren bleiben Ort der fachlichen Regeln.

## 4. MVP-Vorschlag

Der naechste sinnvolle MVP sollte klein bleiben und nur den App-Rahmen beweisen.

MVP-Umfang:

- Hauptfenster mit linker oder oberer Navigation.
- Startseite mit Stammgruppen-/Gruppenuebersicht.
- Schuelerliste fuer ausgewaehlte Stammgruppe bzw. Kurs.
- Schuelerprofil light.
- Bestehender Dialog `+ Schüler` integriert.
- Beobachtungsmaske nur als deaktivierter Platzhalter.
- Berichte/Export nur als Platzhalter.
- Einstellungen nur als Platzhalter fuer spaeteren Datenbankpfad.

Nicht im MVP:

- produktive Beobachtungserfassung
- Kompetenzbewertung
- Dokumentenverwaltung
- Packaging als macOS-App
- Excel-Export-Umbau
- Backup/Restore
- Kurs- oder Stammgruppenverwaltung
- finales Designsystem-Redesign

Ziel:

Eine erste App, die sich wie eine Anwendung anfuehlt, aber fachlich nur Schueler lesen, anzeigen und anlegen kann.

## 5. Empfohlene App-Navigation

Empfohlener Navigationsschnitt:

```text
Jenaplan Kompetenzmanager

Navigation:
- Uebersicht
- Schueler
- Beobachtungen
- Kompetenzen
- Berichte
- Einstellungen

MVP aktiv:
- Uebersicht
- Schueler
- Schuelerprofil light
- Neuer Schueler

MVP Platzhalter:
- Beobachtungen
- Kompetenzen
- Berichte
- Einstellungen
```

Startseite / Uebersicht:

- zeigt Stammgruppen und Kurse als Einstiege
- zeigt Kennzahlen nur, wenn sie aus vorhandenen Daten sauber ableitbar sind
- startet keine Schreibprozesse ausser `+ Schüler`

Schuelerliste:

- filterbar nach Stammgruppe und optional Kurs
- zeigt Name, Stammgruppe, Kurs und Status
- oeffnet Schuelerprofil light ueber `student_id`

Schuelerprofil light:

- zeigt Stammdaten
- zeigt Platzhalter fuer Beobachtungsverlauf
- zeigt Platzhalter fuer Dokumente
- bietet `Neue Beobachtung` nur deaktiviert oder als Platzhalter an

## 6. Datenfluss

Lesender Datenfluss:

```text
PySide6 Screen
-> Desktop Adapter
-> Repository / Query-Service
-> SQLite
-> ViewModel
-> PySide6 Widget
```

Schreibender Datenfluss:

```text
PySide6 Dialog
-> Desktop Adapter
-> CreateStudentCommand
-> ApplicationCommandDispatcher
-> StudentService
-> SQLiteStudentRepository
-> SQLite
-> Screen Refresh aus SQLite
```

Der MVP darf fuer Listen kleine lesende Adapter verwenden.

Wenn lesende Queries komplexer werden, sollten sie nicht in Widgets wachsen, sondern als eigene Query-Services oder Repository-Lesemethoden gekapselt werden.

## 7. Design-System-Uebertragung

Das bestehende Design-System bleibt visuelle Grundlage.

Uebertragung auf PySide6:

| Design-System-Aspekt | PySide6-Mapping |
| --- | --- |
| Desktop-App-Anmutung | `QMainWindow` mit ruhigem App-Shell, klarer Navigation und stabilem Inhaltsbereich |
| Farbwelt | zentrale Stylesheet-Konstanten oder Theme-Modul, keine verstreuten Inline-Farben |
| Typografie | definierte Font-Sizes fuer App-Titel, Abschnittstitel, Labels und Tabellen |
| Kartenlayout | `QFrame`/Custom Widgets fuer Schuelerkarten mit festen Abstaenden |
| Kartenabstaende | zentrale Spacing-Konstanten |
| Suchfeld | `QLineEdit` mit klarer Filterfunktion, keine fachliche Datenveraenderung |
| Dialoge | `QDialog`, klare Pflichtfelder, Abbrechen links, Speichern rechts |
| Statusmeldungen | Statusleiste oder Inline-Fehlerbereich, keine technischen Traces fuer Nutzer |
| Fehlermeldungen | Application-/Domain-Fehler lesbar anzeigen, technische Details im Log |

Keine pixelperfekte Excel-Kopie ist erforderlich.

Wichtig ist eine konsistente, ruhige Desktop-Anwendung, die die freigegebene Informationshierarchie uebernimmt.

## 8. Risiken

Packaging als macOS-App:

- hohes Risiko
- PySide6 muss mit Python, Assets und SQLite-Pfad ausgeliefert werden
- Signierung, Gatekeeper und Updates sind zu klaeren

Datenbankpfad produktiv:

- hohes Risiko
- `data/kompetenzmanager.sqlite` ist fuer Entwicklung plausibel, aber nicht automatisch ein produktiver Nutzerpfad
- Mehrbenutzerbetrieb und Dateiablage sind offen

Backup/Restore:

- hohes Risiko
- SQLite braucht klares Backup-Konzept, Restore-Prozess und Schutz vor versehentlicher Ueberschreibung

Updates:

- mittleres bis hohes Risiko
- App-Updates duerfen SQLite-Schema und bestehende Daten nicht brechen
- Migrationsstrategie fehlt noch

Datei-Export/Berichte:

- mittleres Risiko
- Exportformate muessen separat freigegeben werden
- Export-Builder muessen aus SQLite saubere Ausgabeprojektionen erzeugen

Testbarkeit von PySide6:

- mittleres Risiko
- Adapter- und ViewModel-Tests sind stabil
- echte UI-Klicktests sollten spaeter sparsam und gezielt eingesetzt werden

UI-Aufwand gegenueber Excel:

- mittleres Risiko
- PySide6 erfordert mehr eigenen UI-Aufbau
- dafuer weniger Excel/VBA-macOS-Reibung

Rueckweg zu xlwings:

- niedrig bis mittel, solange Excel/VBA nicht geloescht wird
- Ruecksprungpunkt existiert
- gemeinsame Application-/Domain-/Repository-Schicht reduziert Lock-in

## 9. Nutzen-Aufwand-Vergleich

| Option | Stabilitaet | Aufwand | UX-Potenzial | Risiko | Architekturpassung | Rueckbaubarkeit |
| --- | --- | --- | --- | --- | --- | --- |
| A: PySide6 als Hauptanwendung | hoch fuer App-Interaktion, offen fuer Packaging | mittel bis hoch | hoch | mittel bis hoch | gut, wenn Adapter sauber bleibt | gut, solange Excel erhalten bleibt |
| B: xlwings als Excel-Bruecke | offen | mittel | mittel | mittel bis hoch | moeglich, aber Prozess- und Excel-Abhaengigkeit bleibt | gut |
| C: Excel/VBA-Runtime-Adapter fortfuehren | niedrig bis mittel auf macOS | mittel, aber mit hoher Reibung | begrenzt | hoch | fachlich passend, technisch fragil | gut |

Kurzbewertung:

PySide6 wirkt technisch als naechster Pruefpfad sinnvoller als eine weitere Vertiefung des Excel/VBA-Runtime-Adapters.

Die finale Umstellung auf PySide als Hauptanwendung ist durch ADR-046 erfolgt. Packaging, produktiver Nutzer-Datenbankpfad, Backup/Restore und Exportformate bleiben offene Folgearbeiten.

## 10. Empfehlung fuer naechsten Sprint

Empfohlener naechster Sprint:

```text
PySide6 MVP Shell und Navigation
```

Ziel:

- Hauptfenster mit stabiler Navigation
- Uebersicht / Stammgruppenansicht
- Schuelerliste
- Schuelerprofil light
- bestehender `+ Schüler`-Dialog integriert
- Platzhalter fuer Beobachtungen, Kompetenzen, Berichte und Einstellungen

Nicht enthalten:

- neue fachliche Schreibprozesse
- Beobachtungsmaske
- Packaging
- Excel-Export-Umbau
- Datenmodellmigration

Akzeptanzkriterien:

- App startet.
- Navigation fuehlt sich wie Anwendung an.
- Schueler werden aus SQLite angezeigt.
- Klick auf Schueler oeffnet Profil light.
- `+ Schüler` speichert weiter ueber den bestehenden Command-Stack.
- Keine Businesslogik in Widgets.
- Tests fuer Adapter/ViewModels sind gruen.

## 11. Offene Folgeentscheidungen

- Wo liegt die produktive SQLite-Datei?
- Wie funktionieren Backup und Restore?
- Wie werden Schema-Migrationen versioniert?
- Wie wird die App fuer macOS paketiert?
- Wie werden Excel-Berichte und Exporte aus SQLite erzeugt?
- Wie wird das Design-System in PySide6 technisch zentralisiert?
- Welche UI-Tests sind stabil genug fuer den Alltag?
