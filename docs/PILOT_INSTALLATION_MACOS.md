# macOS-Installation und technische Pilotvorbereitung

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

Diese Anleitung beschreibt den lokalen Build-405-Kandidaten. Die Veröffentlichung
und die öffentliche Auslieferungsprüfung benötigen einen gesonderten Auftrag.
Historische Buildnachweise gelten jeweils nur für die dort identifizierten
Artefakte; geänderte Pakete benötigen neue passende Nachweise.

| Punkt | Build 405 |
|---|---|
| Architektur | Apple Silicon (arm64) |
| Mindestplattform | macOS 13 |
| Installation | Drag-and-drop-DMG |
| Signatur | Ad-hoc-Codesignatur; keine Developer ID oder Notarisierung |
| Frischer Start | Leerer verschlüsselter Final-V4-Bestand |
| V7-Aktivierung | Bewusste betreute Wartung nach abgeschlossenem First Run |
| Updatekanal | Bestehender Pilotkanal; Stable deaktiviert |

## Installation und erster Start

1. Die freigegebene DMG-Datei und die dazugehörigen Prüfsummen verwenden.
2. Alle laufenden Instanzen des Kompetenzmanagers vollständig beenden.
3. DMG im Finder öffnen, `Jenaplan-Kompetenzmanager.app` nach `Programme`
   ziehen und das Kopieren abwarten. Bei einem Update die vorhandene App ersetzen.
4. DMG auswerfen und die App aus `Programme` starten.
5. Unter `Über die App` Version {{PILOT_VERSION}} und Build {{PILOT_BUILD}}
   prüfen.

Der normale Lehrkraftbetrieb benötigt weder Python noch Repository oder
Entwicklungsumgebung. Der ausdrückliche V7-Wartungsstart wird durch die
Pilotbetreuung im Terminal vorgenommen.

Der Pilot ist ad-hoc signiert und nicht notarisiert. macOS kann den ersten
Start blockieren. Den Systemhinweis schließen, im Finder mit Control-Klick
`Öffnen` wählen oder unter `Systemeinstellungen > Datenschutz & Sicherheit`
nur diese App mit `Dennoch öffnen` freigeben. Gatekeeper nicht global
abschalten. Eine erfolgreiche Ad-hoc-Signaturprüfung ist keine Apple-
Notarisierung oder allgemeine Gatekeeper-Freigabe.

Bei einer frischen Installation ein App-Passwort mit mindestens 15 Zeichen
anlegen und die zehn einmalig angezeigten Recovery-Codes außerhalb des Macs
sicher aufbewahren. Beim Update mit dem bestehenden Passwort anmelden; kein
neues Konto und keinen neuen Datenbereich anlegen.

## Datenhaltung: Final V4 und V7

Build 405 kann den bestehenden Final-V4-Bestand sowie den bewusst umgestellten
V7-Bestand öffnen. Ein gewöhnlicher Start stellt Final V4 nicht um. Die
neuen Unterrichtszeitvorlagen, Stammgruppen-/Mehrfachfachstunden und
A-/B-Wochen benötigen V7.

Fachdatenbank und Dokument-Companion werden mit SQLCipher 4.17.0,
SQLite 3.53.3 und CommonCrypto geöffnet. Standard-SQLite ist kein Fallback.
Das App-Passwort schützt die Anmeldung. Der getrennte Datenschlüssel DMK
wird über den macOS-Schlüsselbund geschützt; ein separater Database-Key
öffnet die Datenbanken. Fehlende oder widersprüchliche Schlüssel-, Schema-
oder Runtimezustände blockieren den Start.

Der First Run erzeugt den technischen Final-V4-Systembestand, Schuljahr
`2026/27` vom 01.08.2026 bis 31.07.2027 und den offiziellen Katalog mit
331 Kompetenzen. Schüler, Stammgruppen, Kurse, Kursverbünde, Beobachtungen,
Bestätigungen, Berichtsentwürfe, LEG-Entwürfe, Testdokumente,
Beispielschüler, Beispielbeobachtungen und Testbackups bleiben leer.
Auch ein neuer Bestand wird erst nach abgeschlossenem First Run bewusst auf
V7 umgestellt.

## Betreutes Update von 0.4.4 / Build 404

### Vorbereiten

1. Vorhandenes App-Passwort, sichere Recovery-Codes und Zugang zum ursprünglichen
   macOS-Benutzerkonto sicherstellen. Schlüsselbundobjekte erhalten.
2. In Build 404 unter `Einstellungen > Datensicherung` mit `Backup erstellen`
   ein vollständiges verschlüsseltes `.jkmebackup` anlegen und mit
   `Backup prüfen …` prüfen. Den Sicherungszeitpunkt festhalten und die
   Sicherung geschützt aufbewahren.
3. Genügend freien Speicher für App, Bestand und vollständige Sicherungen
   bereitstellen. Anschließend die App vollständig beenden und Build 405 wie
   oben installieren.
4. Im gewöhnlichen Build-405-Start die bestehende Anmeldung und den vorhandenen
   V4-Bestand prüfen. Danach die App wieder vollständig beenden.

Ein extern aufbewahrtes `.jkmebackup` bleibt vom ursprünglichen lokalen
Schlüsselkontext abhängig. Es ist kein unabhängig auf jedem anderen Mac
nutzbares Wiederherstellungsmedium.

### V4 bewusst auf V7 umstellen

Die Pilotbetreuung ermittelt den bestehenden kanonischen Datenroot. Im
Standardfall liegt er unter `~/Library/Application Support/Jenaplan-Kompetenzmanager`.
Für den Wartungsstart ist dessen vollständiger absoluter, aufgelöster Pfad
anzugeben. Nicht auf einen neuen Ordner, eine Datenkopie oder einen
Testbestand zeigen.

Die folgende Befehlsform ist eine Vorlage für die Betreuung. Den Platzhalter
durch den tatsächlichen bestehenden Datenroot ersetzen:

```sh
JKM_APP="/Applications/Jenaplan-Kompetenzmanager.app"
"$JKM_APP/Contents/MacOS/Jenaplan-Kompetenzmanager" \
  --migrate-v4-to-v7 \
  --runtime-root "<bestehender kanonischer Datenroot>"
```

Die Wartung lädt ausschließlich vorhandene Schlüssel, prüft Installation und
exaktes V4-Quellschema, erzeugt ein verschlüsseltes vollständiges Quellbackup
und prüft dessen Inhalt mit dem unabhängigen Backupprüfpfad. Die Migration
beginnt erst nach dieser Prüfung. Unter exklusiver Wartung werden die
Verbindungen geschlossen und die Umstellung transaktional ausgeführt.
Keine zweite App starten, keine Dateien austauschen und die Wartung nicht
absichtlich unterbrechen.

Das Quellbackup wird im bestehenden Datenroot unter
`schema-upgrade-source/transaction-timetable-weeks-v1/source.jkmebackup`
aufbewahrt. Dieser Pfad samt Abschlussbeleg gehört zum geschützten Bestand;
keine Datei daraus löschen oder einzeln zurückkopieren.

Nach erfolgreicher Transaktion prüft die mit frischem Programmabbild
gestartete Abschlussprüfung den vollständigen Zielbestand einschließlich
Dokumenten erneut. Erst danach
entsteht der authentisierte Abschlussbeleg und die App startet normal neu.
Mit dem bisherigen Passwort anmelden. Es werden keine Datenschlüssel neu
angelegt oder rotiert.

### Ergebnis prüfen und Fehler behandeln

Nach dem Neustart Kinder, Stammgruppen/Kurse, vorhandene Beobachtungen und
Kompetenzstände stichprobenartig prüfen, vorhandene Dokumente öffnen und
Stundenplan sowie Bericht-/LEG-Stände kontrollieren. Unter
`Einstellungen > Unterrichtszeiten` und `Einstellungen > Stundenplan` sind
nun die V7-Funktionen verfügbar. Ein neues V7-`.jkmebackup` erstellen und
mit `Backup prüfen …` prüfen. Die V4-Sicherung weiterhin getrennt erhalten.

Bei `Wartung sicher angehalten` den angezeigten Fehlercode notieren,
Bestand und Quellbackup erhalten und die Pilotbetreuung hinzuziehen.
Ein gewöhnlicher Neustart umgeht den sicheren Halt nicht. Nur wenn die
Transaktion bereits vollständig committet ist und lediglich die
Abschlussprüfung fehlt, kann die Betreuung denselben App-Aufruf mit
`--complete-v7-migration` statt `--migrate-v4-to-v7` verwenden. Dieser
Befehl migriert nicht erneut; er prüft den vollständigen Zielbestand und
dessen Quelle erneut. Er ist keine allgemeine Reparatur für jeden Abbruch.
Keine Belege löschen und keinen fehlenden Schlüssel neu erzeugen.

### Rückkehr zu V4

Build 404 kann eine V7-Datenbank nicht öffnen. Das bloße Neuinstallieren von
Build 404 macht die Migration nicht rückgängig. Eine betreute Rückkehr
benötigt eine geeignete vollständige geprüfte V4-Sicherung und den passenden
ursprünglichen Schlüsselkontext. Änderungen seit diesem Sicherungszeitpunkt
können dabei verloren gehen. Die V7-Wiederherstellungsfunktion ist kein
Downgrade-Werkzeug. Keine einzelne Datenbankdatei oder Schlüsseldatei
manuell zurückkopieren.

## Dokumente, Backup und Auth-Recovery

Beobachtungsanhänge, Schülerdokumente sowie finale Bericht- und LEG-PDFs
werden verschlüsselt als Managed Documents gespeichert. Der sichere
In-App-Viewer bietet mehrseitige Anzeige, Scrollen, Zoom und erneutes Öffnen.
Export, Drucken und Teilen aus diesem Viewer werden nicht zugesagt. Die
bewusste separate Kompetenzübersicht als PDF ist eine eigene Exportfunktion;
ihre ausgegebenen Dateien müssen geschützt abgelegt werden.

Das Fachbackup enthält Hauptdatenbank, Dokument-Companion, Schlüsselmetadaten
und verwaltete verschlüsselte Dokumentcontainer. Es enthält weder DMK noch
App-Passwort oder Recovery-Codes; auch Authentifizierungsdatenbank und
App-Einstellungen werden damit nicht als vollständige Installation gesichert.

Produktbackups sind ausschließlich verschlüsselte `.jkmebackup`. Restore
verlangt Prüfung, Vorschau und Bestätigung, verifiziertes Staging,
Safety-Backup, separaten Worker, vollständige App-Beendigung, kontrollierten
Neustart und erneute Anmeldung. V4- und V7-Sicherungen werden anhand ihrer
jeweiligen exakten Schemaidentität geprüft. Allgemeine Geräteportabilität,
Cloud-Sicherung und Wiederherstellung eines verlorenen DMK sind nicht
implementiert. Einzelheiten stehen in `PILOT_BACKUP.md` und
`SICHERHEIT_UND_VERSCHLUESSELUNG.md`.

Recovery-Codes sind der erste Weg bei verlorenem App-Passwort; sie ersetzen
keinen fehlenden lokalen Datenschlüssel. Der vorhandene betreute Support
Reset gilt ausschließlich für einen intakten Final-V4-Bestand mit
zugreifbarem DMK und erfolgreich erzeugtem und geprüftem Safety-Backup.
Für V7 ist kein entsprechender Support-Resetadapter vorhanden. Allgemeine
Reset-Hinweise der Oberfläche erweitern diese Grenze nicht.

## Fehlerbehebung und sichere Supportgrenzen

### Selbst sicher prüfen

- **App startet nicht:** App nur einmal aus `Programme` öffnen. Version,
  macOS-Hinweis und angezeigten Fehlercode prüfen. Bei Gatekeeper nur die
  kontrollierte Freigabe oben verwenden.
- **Schlüsselbund gesperrt oder Zugriff verweigert:** Im ursprünglichen
  macOS-Benutzerkonto anmelden und den eigenen Schlüsselbund auf normalem
  macOS-Weg entsperren. Eine erwartete Systemfreigabe nur für die geprüfte
  App bestätigen. Keine Schlüsselobjekte löschen oder neu erzeugen.
- **Anmeldung nicht möglich:** Eingabesprache und Feststelltaste prüfen.
  Angezeigte Wartezeit beachten. Bei verlorenem Passwort einen noch
  unbenutzten Code über `Recovery-Code verwenden` einsetzen.
- **Stundenplanänderung nicht sichtbar:** Prüfen, ob gespeichert wurde,
  richtiger Wochentag und Kalenderwoche gewählt sind und `Gültige Woche`
  angezeigt wird. A-/B-Vorschau ändert keine Daten. Gültigkeit, Aktivstatus
  und Einzelwochenkorrektur kontrollieren. Nach einer Zeitvorlagenänderung
  bleiben bereits gespeicherte Stunden absichtlich unverändert; sie müssen
  einzeln bearbeitet werden. Fehlen V7-Bedienelemente, ist ein noch nicht
  umgestellter V4-Bestand möglich.

### Betreuung erforderlich, keine eigenständige Dateireparatur

- **Datenbankintegrität fehlerhaft:** Arbeit einstellen, Meldung notieren,
  vorhandenen Bestand und Sicherungen erhalten. Keine Datenbank mit einem
  anderen Programm öffnen oder unverschlüsselt neu anlegen.
- **Upgrade unvollständig:** Wartungsfehler und Zeitpunkt festhalten.
  Abschlussprüfung nur nach Einordnung durch die Betreuung, wie oben beschrieben.
- **Backup nicht akzeptiert:** Fehlermeldung notieren und prüfen, ob die
  unveränderte `.jkmebackup` zur ursprünglichen Installation und zum
  passenden Schema gehört. Keine Archivdateien umbenennen oder entpackte
  Einzeldateien importieren. Eine abgewiesene Prüfung nicht umgehen.
- **Restore nicht möglich:** Bestand, gewählte Sicherung und Safety-Backup
  erhalten. Nicht in laufende Worker- oder Neustartprozesse eingreifen.
  Vor einer erneuten Wiederherstellung den tatsächlichen Zustand durch
  die Betreuung klären lassen.
- **Datenbankschema inkompatibel / alte App nach Migration gestartet:**
  Build unter `Über die App` beziehungsweise anhand der gestarteten Datei
  prüfen. Eine V7-Installation mit Build 405 starten. Bei Build 404 ist die
  V7-Ablehnung erwartet; kein neues Konto, kein Reset und kein Downgrade
  durch bloßen Austausch der App. Bei weiterem sicheren Halt Betreuung
  hinzuziehen.

An den Support zunächst Version/Build, Zeitpunkt, Handlung und den
personenfreien Fehlercode übermitteln. Keine Passwörter, Schlüssel,
Recovery-Codes, vollständigen personenbezogenen Daten oder Backupinhalte
ungeschützt senden. Screenshots vorher auf Namen und Dokumentinhalte
prüfen. Ein Support-Reset ist kein Reparaturweg für beschädigte Daten,
fehlende Schlüssel, Schemafehler oder eine unvollständige Migration.

## Noch vor Veröffentlichung

Der finale Artefaktstand benötigt ausdrückliche PO-Freigabe sowie die zum
tatsächlichen Paket passenden Dokument-, Hash- und Paketnachweise. Die
öffentliche Prüfung der Assets, Notes und signierten Sparkle-Auslieferung
folgt erst im gesonderten Veröffentlichungsauftrag. Developer ID,
Notarisierung, portable Recovery oder ein Stable-Rollout werden für diesen
Pilot nicht behauptet.
