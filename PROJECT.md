# Projektdokumentation: Jenaplan-Kompetenzmanager

## iPad-Simulator: UX-Verfeinerung geprüft – 12.10.2026

Die aktuelle Prüfrunde ist abgeschlossen: eigene Suchzeile und Filter, Touch-Auswahlmenüs, einspaltige Bericht-/LEG-Arbeitsseiten, responsive Berichtsvorschau und Abschlussleisten oberhalb der Bildschirmtastatur. Bereichsauswahl aktualisiert vorhandene Inhalte, Wischgesten funktionieren auch in verschachtelten Simulator-Scrollflächen. Dokumentationsring beendet QPainter explizit; im letzten Profil-/Scrolllauf keine QPainter-/BackingStore-Warnung mehr.

Native Nachweise: Eingabe „Test“ über die Softwaretastatur, als LEG-Entwurf gespeichert und nach Neuinstallation erhalten. Hoch-/Querformat mit Tastatur sichtbar bedienbar. Berichts-Entwurfschutz: Weiterbearbeiten und Verwerfen der ungespeicherten Teständerung geprüft. Schüler-Pflichtfeldprüfung sichtbar, Abbruch ohne Anlage. Vollständiger Kompetenzexport: 329 synthetische Stände über den bestehenden Adapter vorbereitet, zwei offene Stände ausdrücklich im UI gewählt; Export vorher gesperrt. Native PDF mit 29 Seiten und Pflanzen/Balken erzeugt, interne Bestätigungsformulierungen fehlen; Teilen bewusst abgebrochen, temporäre Datei entfernt.

Validierung: 14 Tablet-/Fensterprüfungen, 28 Kompetenz-/Berichts-PDF-Prüfungen, separat 12 Beobachtungs- und 16 Navigationsprüfungen bestanden. ARM64-Simulatorbuild und tiefe strikte Ad-hoc-Signaturprüfung bestanden. Quellstaging verweigert Checkout/Produktordner und Symlinks; Konfiguration unabhängig vom ersten Kleinstprototyp. Aktuelle Bilder: output/ipad-app/screenshots/refined/index.html; PDF-Beleg: output/ipad-app/Kompetenzexport-Simulator-Mila.pdf.

Dies ist ein Simulator-Teststand ausschließlich mit erfundenen Daten, keine vollständige Geräte-/Produktabnahme. Vor realer Nutzung offen: Gerätesignierung und echtes iPad; Files-Import, Backup/Restore, App-/Dateischutz, vollständige Accessibility-Abnahme und Langzeittest einschließlich Abbruch während des Teilens. Desktop-Sicherheits-/Update-/Backup-Funktionen sind im iPad-Test sichtbar deaktiviert. Qt-Testmodus bleibt separat; Mac-Produktdaten, Schlüssel, Veröffentlichung und Final-V4-Schema unverändert. Der bekannte kombinierte Qt-Pytest-Teardownfehler am unveränderten HEAD wird nicht als bestandene Gesamtsuite dargestellt.


## Gesamte iPad-Test-App – Umsetzung 12.10.2026

PO-Auftrag: gesamte App im bestehenden Design für iPad, eigene lokale Daten, zunächst Simulator und ausschließlich synthetische Daten. Separate Tablet-Komposition mit ursprünglichen Domain-/Application-/Repository-/ViewModel-Verträgen und unverändertem Final-V4-Schema. Touch-Schülerkarten, Navigation im Hochformat, Profilaktionen und geführte Beobachtungsschritte; Eingaben als Seiten statt Desktopfenster. PDF-Code mit offiziellen iOS-Pillow-/reinen ReportLab-Paketen und nativem UIKit-Teilen vorbereitet. Mac-Startup, Verschlüsselung und Veröffentlichung unverändert.

Technische iOS-Anpassungen: Qt-Typen vor Nutzung vollständig initialisieren, kein globaler Python-Eventfilter während C++-Widgetkonstruktion, iOS ohne Offscreen-Opacity-/Card-Shadow-Effekte. App-Containerbindung über feste Bundle-/Rootrolle statt wandelbarem absolutem Pfad. PO stellt Bedienhilfen wegen LLDB-bestätigtem Qt-iOS-Accessibility-Absturz vorerst zurück; ausschließlich in dieser Test-App deaktiviert. Kein Systemsetting und keine Accessibility-Freigabe.

Simulatorbuild/Start und Navigation einschließlich Profil, Stammdaten, Einstellungen, Bericht und LEG geprüft. Eine synthetische Beobachtung mit Kompetenzrating über die Oberfläche gespeichert und nach erneuter Installation wieder angezeigt. Beobachtungsschritte einschließlich Weiter-Aktionen und 44-Pixel-Bewertungen sichtbar bedienbar; bei Bildschirmtastatur bleiben Abschlussaktionen erreichbar. Berichtsvorschau und natives Teilen eines erzeugten PDFs erreicht, Share-Sheet bewusst abgebrochen. 24 echte Screenshots als Galerie, ZIP und PDF unter output/ipad-app/screenshots/ und output/pdf/ gesichert. Sechs Tablet-Tests und 26 Präsentations-/Berichts-PDF-Tests bestanden. Noch offen: Hochformat-Reflow im Bericht/LEG, Profil-Filterbreite, vollständiger Kompetenz-PDF-Pfad und weitere Plattformabnahmen. Kein vollständiger UI-Abschluss behauptet. Desktopadapter: 298 Tests/50 Untertests bestanden; separat 12 Beobachtungs- und 16 Sidebarchecks bestanden. Kombinierter Pytest-Qt-Teardown mit Signal 139 ist am unveränderten HEAD ebenso reproduziert; Einzelprozesse beenden regulär. Gerätebuild, echte Hardware, Files-Import/Backup/Restore, App-Schutz und Produktionsfreigabe bleiben separate offene Abnahmen. Keine realen Schülerdaten verwenden.


## iPad-Simulatortest bestanden – 11.10.2026

Nach dem Mac-Neustart ist der separate Qt/PySide-6.12.0-Prototyp unter iPadOS 27.0 installiert und gestartet. Drei synthetische Auswahlen über die Simulatoroberfläche gespeichert; separate SQLite-Datei im eigenen App-Container enthält exakt die gewählten Werte. Nach vollständigem Beenden und erneutem Start zeigt die Oberfläche dieselben Werte. Hoch- und Querformat visuell lesbar. ARM64-Build und tiefe strikte Ad-hoc-Signaturprüfung bestanden; drei Quelltests und Host-Fensterprüfung waren bereits bestanden. Dauerhafte lokale Buildbelege unter output/ipad-prototype/; Details in prototypes/ipad/README.md.

Dies belegt PySide-/SQLite-Grundfunktionen im Simulator, keine vollständige Produktportierung. Echte Hardware, Pflanzen-PDF und natives Teilen, Dateischutzattribute/Sperrverhalten und Gerätesignierung bleiben offen. Nur erfundene Daten, keine zusätzliche App-Verschlüsselung im ausdrücklich freigegebenen Test; kein Produktmodell geändert, keine Mac-Sicherheitsanforderungen abgesenkt und kein Produktbuild veröffentlicht.

Historie: Der erste erfolgreiche Build konnte vor dem Mac-Neustart wegen Device-Hub-/Simulator-Timeouts nicht installiert werden. Diese Infrastrukturblockade ist jetzt überwunden; der ursprünglich fehlende Xcode-Stand ist erledigt.

## Veröffentlicht: 0.4.3 / Build 403 – 11.10.2026

GitHub-Pre-Release `v0.4.3-build403` und Pilot-Appcast veröffentlicht; öffentliche Endprüfung erfolgreich. Paketquelle ist exakt `d531e11584e3cc7b7b2b79ca0ca807fc2efe3287`; nachfolgende Release-Werkzeugkorrekturen ändern keine Paketbytes. Vier öffentliche Assets wurden mit Größe und SHA256 zurückgeprüft; Ed25519-Signaturen für DMG, Release-Notes und Feed gültig. Alle elf Originalpaketgates bestanden. Restore-Worker-Smoke erreicht RESTORE_READY und bricht kontrolliert vor Datenaustausch ab; keine vollständige Restore-Abnahme. Stable bleibt deaktiviert, keine Developer-ID-/Notarisierungsfreigabe behauptet.

Nachweise: Gesamtsuite 2.472 Tests und 100 Untertests bestanden, 104 übersprungen; ein Test setzte einen Arbeitsordner außerhalb des Systemtemps voraus und scheiterte im temporären Release-Checkout. Alle 29 Runtime-Root-Tests mit identischem Quellstand im regulären Projektordner bestanden. Zusätzlich 94 Tests im exakten SQLCipher-4.17-Stack und sechs reale synthetische Keychain-Prozesstests bestanden. Release-Werkzeugkorrekturen: 43 gezielte Tests bestanden. Historische SQLCipher-4.12-Infrastrukturtests sind keine Tests des 4.17-Profils. Paketierter Elternexport unabhängig geprüft: zwölf Bereiche, 331 Kompetenzen, 29 Seiten, vier Alphamasken; unvollständiger Stand blockiert. Alle 35 Seiten der fünf Begleit-PDFs visuell geprüft. Finder-Installationsfenster mit drei lesbaren Zielen geprüft, keine App gestartet oder installiert.

Manifest und unveränderte Artefakte lokal unter `release/output/0.4.3-build403-d531e11584e3/`; DMG-SHA256 `c49aa8b227a8ec13abb9e5ae492089bf5f9f7f9d47aa3977c23d280327cf1bc5`. Öffentlicher Release: https://github.com/JoergG87/Jenaplan-Kompetenzmanager-Update/releases/tag/v0.4.3-build403. Die vom Nutzer verschobene Pflanzen-ZIP bleibt im Arbeitsordner unangetastet. Frühere Kandidaten 401/402 bleiben historisch und unverändert.


## Releasevorbereitung 0.4.3 / Build 403 – 11.10.2026

PO-Auftrag: alle notwendigen Arbeiten bis zur Veröffentlichung im bestehenden Pilotkanal durchführen. Quellbasis ist die geprüfte Elternexport-Umsetzung `5736ce1`; neue monotone Paketidentität 0.4.3 / Build 403. Build 402 bleibt unverändert und wird nicht veröffentlicht. Saubere separate Release-Kopie erhält die im Arbeitsordner bewusst verschobene Pflanzen-ZIP aus dem geprüften Commit; der Arbeitsordner bleibt an dieser Stelle unverändert. Gesamtsuite am finalen Versionscommit, elf Originalpaketgates und paketierter Restore-Worker-Smoke sind vor Publikation erforderlich. Keine produktive App starten, keine Produktdaten oder bestehenden Produktschlüssel ändern. Veröffentlichung erfolgt als GitHub-Pre-Release und Pilot-Appcast; Stable bleibt deaktiviert. Paketprüfung und öffentliche Endverifikation stehen noch aus.


## Elternexport – PO-Präzisierung 11.10.2026

Eltern-PDF ohne Bestätigungsterminologie/Datum. Export erst nach vollständiger expliziter Auswahl im aktuellen Katalog; offene Kompetenzen im Dialog nachtragen und atomar als bestehende Bestätigungen speichern. Katalogänderungen vor Speicherung/Ausgabe erneut prüfen. Globalen abgeschnittenen Shell-Toast korrigieren. Kein Schemawechsel, keine automatische Bewertung; reale Testkopie und Paketfreigabe bleiben getrennt. Quellumsetzung abgeschlossen: 2.469 Tests / 100 Untertests bestanden (104 übersprungen); nach Bildintegration zusätzlich 29 gezielte Tests und der exakte SQLCipher-4.17-Anwendungsstack-Test bestanden. Vier transparente PNGs samt ZIP und Promptset liegen unter assets/competency_plants; PDF-Vorschau visuell geprüft, alle vier eingebetteten Alphamasken getestet. Gebundene Testkopie neu gebaut und separat ad-hoc signiert; Testkonto erhalten, Jonas mit ausschließlich fiktiven Ständen vollständig vorbereitet. Realer Ergänzungsdialog bei Mila mit 283 offenen Ständen und gesperrtem Weiter-Button geprüft; Abbruch ohne Ergänzung. Jonas exportiert nach Downloads: zwölf Bereiche, alle 331 Katalogtexte, 29 Seiten; keine internen Bestätigungstexte, Alphakanäle in allen eingebetteten Pflanzen erhalten. Reale Nachprüfung abgeschlossen: Fachreiter im Ergänzungsdialog vollständig lesbar und scrollbar; Erfolgsmeldung nach erneutem Downloads-Export mit langem Dateinamen in beiden Zeilen vollständig sichtbar. Neuer sauberer Paketkandidat mit eigener Buildnummer und Paketgates bleibt vor Veröffentlichung erforderlich.


## Paketstand 0.4.2 / Build 402 – reale Exportabnahme fehlgeschlagen

Das neue lokale Paket aus `2ac4e28ca5ea1545445922f228ac941bd944e190` ist erstellt. Alle elf Paketgates und der paketierte Restore-Worker-Smoke bestehen. Quellprüfung: 2.457 Tests / 100 Untertests; separat 94 exakte Cipher-Tests plus sechs reale synthetische Keychain-Prozesstests. Das offizielle Kompetenz-PDF mit Pflanzen ist enthalten. Manifest und genaue Abnahmegrenzen stehen in SPRINTS.md. Veröffentlichung und letzte reale PO-Bedienabnahme bleiben offen; Build 400 bleibt veröffentlicht, 401 unverändert lokal.

## Aktueller Updateauftrag – 11.10.2026

Der originale Paketkandidat 402 bleibt wegen der fehlgeschlagenen Downloads-Ausgabe NO-GO. Die Quellkorrektur und eine getrennte, erneut signierte und fest gebundene Testkopie bestehen nun die reale Exportprüfung: 31 Seiten, zwölf Bereiche, alle 331 Katalogtexte; 86 gezielte Tests bestanden. Ansichtsfilter verkürzen den Export nicht mehr. Testkonto und synthetischer Datenroot wurden erhalten. Die weitere Dialogkorrektur verwendet den nativen macOS-Speicherdialog und expliziten Erfolgston; 64 gezielte Tests bestehen. Finale reale Dialogabnahme benötigt das Entsperren der Testkopie. Ein neuer sauberer Paketkandidat mit eigener Buildnummer und vollständigen Paketgates ist vor einer Veröffentlichung erforderlich.

PO-freigegeben ist der PDF-Export der Kompetenzübersicht mit den Originalpflanzen. Die neue Quellidentität ist 0.4.2 / Build 402; das unveränderte Paket 401 wird nicht ersetzt. Der Export nutzt bestätigte kanonische Stände und keine automatisch übernommenen Vorschläge, bleibt schemafrei und speichert ausschließlich eine bewusst gewählte externe unverschlüsselte PDF-Datei. Für Paket 401 bestand die Wiederholungsprüfung vom 11.10. alle elf Gates plus Restore-Worker-Smoke (Abbruch vor Datenaustausch). Die darunterstehenden NO-GO-Befunde sind der historische Stand vom 08.09.; die damalige Fehlerursache ist nicht bewiesen. Neue Paketfreigabe und Veröffentlichung werden ausschließlich an den neuen sauberen Quellcommit gebunden.


## Release-Baseline und aktueller Quellstand

Der veröffentlichte macOS-Pilotstand ist Version `0.4.0` / Build `400` aus
Commit `e96a77e328da98bfb3622201110e6e08c8b3e312`. Der annotierte Tag
`v0.4.0-build400` zeigt auf genau diesen Commit. Dieser veröffentlichte Stand
ist eine unveränderliche Referenz: Er wird weder neu gebaut noch unter
derselben Buildnummer aus einem anderen Quellstand erneut paketiert oder
veröffentlicht.

Der erste Produktfix nach der veröffentlichten Referenz,
`926582f7db3a44642b05301fbbb676a91a1f500c`, korrigiert die
individuelle schuljahresbezogene Fachrelevanz der Dashboard-Heatmap und von
`Passende Kinder für diese Stunde`. Diese Korrektur ist umgesetzt, aber nicht
als neuer Build veröffentlicht. Für das am 08.09.2026 mit freier Hand
beauftragte Folgeupdate ist die neue Quellidentität `0.4.1` / Build `401`
festgelegt. Das lokale Paket aus `ad4bd32` scheiterte am 08.09. zunächst beim Erststart
mit `data_master_key_access_denied`. Die unveränderte Wiederholungsprüfung
vom 11.10. bestand alle elf Paketgates und den Restore-Worker-Smoke. Die
ursprüngliche Ursache bleibt ungeklärt; neue Funktionen werden ausschließlich
als 0.4.2 / Build 402 gebaut. Nachweise und getrennte Abnahmen stehen in `SPRINTS.md`. Die veröffentlichte Basis bleibt
davon getrennt unverändert.

## Aktuelle Weiterarbeit – freigegeben am 07.09.2026

Der Product Owner hat die Vorbereitung des Dashboard-Folgeupdates, fünf
kleine Komfortfunktionen und die fachlich-technische Vorbereitung des
Schülerlisten-Imports beauftragt. Die fünf Funktionen sind: Tastaturzugang
`⌘N` zur Beobachtung, Weitererfassen nach erfolgreichem Speichern,
verlässlicher Eingabefokus, einklappbare Fachbereiche der Berichtsvorschau
und ein dezenter Datensicherungshinweis. Details, Abnahmen und aktueller
Umsetzungsstatus stehen im entsprechenden Abschnitt von `SPRINTS.md`.

Die Umsetzung verwendet die vorhandenen Daten- und Schreibverträge. Der
Import bleibt bis zur Entscheidung über Identität, Dubletten und atomare
Zuordnungen ein Vorbereitungspaket. Die sichtbare Bedienprüfung erfolgt
per Computer-Use an einer getrennten Instanz mit synthetischen Daten.
Alle fünf Funktionen sind implementiert und einzeln nach passenden Tests
und sichtbarer synthetischer Prüfung committet. Die konkreten Nachweise stehen
in `SPRINTS.md`; die verbleibende Alltagsabnahme steht in Backlog-Kategorie B.
Die abgeschlossene Import-Discovery mit CSV-Vertrag, Identitätsgrenzen,
atomarem Schreibkonzept und Abnahmefällen steht in `BACKLOG.md`.

## Vorbereitung des nächsten kleinen Updates

Der Umfang enthält den Dashboard-Fachrelevanzfix, die fünf oben genannten
Komfortfunktionen und den am 11.10. freigegebenen Kompetenz-PDF-Export. `docs/RELEASE_NOTES.md` enthält die vorbereitete
Nutzerbeschreibung; `SPRINTS.md` führt die technischen und sichtbaren Nachweise.
Der Schülerlisten-Import gehört ausschließlich als Discovery zur Weiterarbeit
und ist kein auszulieferndes Feature dieses Updates.

Die veröffentlichte Referenz wurde am 07.09.2026 gegen Git-Tag, GitHub-Release,
Manifest und die vier lokalen Releaseartefakte geprüft. Veröffentlicht bleibt
`v0.4.0-build400` aus `e96a77e`; neue lokale Commits sind davon getrennt.
Das lokale Paket 0.4.1 / Build 401 ist erstellt und am 11.10. technisch erneut
geprüft; es enthält den neuen Export nicht und wird nicht veröffentlicht.
Ein Push, Tag oder Release wurde nicht erzeugt. Alle
Paket-/Cipher-/Releaseprüfungen bleiben an den exakten neuen Quellcommit
gebunden. Synthetische Cocoa-Bedienprüfungen ersetzen weder
Tests am verschlüsselten App-Bundle noch Apple- oder schulische Freigaben.

Die anschließende Diagnose am 08.09.2026 sichert automatische Teststarts
über eine eigene temporäre App-Identität und einen gebundenen Launcher ab.
55 gezielte Tests und die sichtbare leere Ersteinrichtung per Computer-Use
bestanden. Die damalige separate native Diagnose bestätigte `SecItemAdd=-25293`
auch nach manuellem Entsperren; Vertrauensreferenz und ACL-Erzeugung bestanden.
Am 11.10. besteht der Roundtrip außerhalb der Sandbox einschließlich Löschen.
Die Ursache der verweigerten Schlüsselerzeugung ist weiter offen. Eine
fehlende Developer-ID ist damit nicht als Ursache bewiesen. Produktcode,
installierte App und Releaseartefakte wurden in diesem Diagnoseschritt nicht
verändert. Die Testkopie besitzt eine andere Signatur und qualifiziert das
Originalpaket ausdrücklich nicht.

## Pilot-Produktionsschutz im laufenden Betrieb

Der integrierte Fünf-Schritt-Onboardingflow und der veröffentlichte Build 400
verwenden denselben Final-V4-Produktvertrag. Historische Build-302- und
Build-303-PDFs bleiben getrennte Belege und keine aktuelle Pilotunterlage.

Der reale Pilotroot ist ab dem ersten technischen Initialisierungsschritt über
den atomaren, nicht geheimen Marker `.jkm-runtime-root-v1` als
`pilot_product` geschützt. Seeder, Vergleichsdaten, Reset, Force, Recreate und
datenroot-mutierende Developer-/Testwerkzeuge sowie Runtime-/Datenroot
übernehmende Smoke-/Buildwerkzeuge können diesen Schutz nicht aufheben.
Kontrollierte synthetische Tests verwenden getrennte, frisch erzeugte
`synthetic_test`-Roots.

First Run erzeugt ausschließlich die Final-V4-Systemdaten, Schuljahr
`2026/27` (01.08.2026–31.07.2027) und 331 offizielle Kompetenzen. Der Root wird
erst danach aktiv. Restart prüft Katalog, Security Store, DMK/Envelope,
Hauptdatenbank, Companion und Managed Documents fail-closed und ohne stillen
Katalog-Upsert, Migration, Keyrotation oder Datenbankneuerzeugung. Für eine
spätere Datenmigration bleibt ein erfolgreich erzeugtes und verifiziertes
verschlüsseltes `.jkmebackup` vor der ersten Datenmutation verpflichtend; ein
solcher allgemeiner Produktmigrationspfad wird hier nicht neu eingeführt.

## Veröffentlichter Pilotstand 0.4.0 / Build 400

**Status:** Final V4 ist der aktuelle Pilot-/Produktschemavertrag. Der normale
frische Produktstart verwendet keyed SQLCipher 4.17, den getrennt über DMK im
macOS-Keychain-Kontext und Database-Key-Envelope komponierten Datenbankzugriff,
den keyed Dokument-Companion und den zentralen `ManagedDocumentStore`. Es gibt
keinen produktiven Standard-SQLite-, Klartextdokument- oder ZIP-v1-Fallback.
Vorhandene Klartext-, V3- und alte Testbestände werden nicht automatisch
migriert; für den veröffentlichten Pilotstand existierten keine produktiven
Altdaten.

Beobachtungsanhänge, allgemeine Schülerdokumente sowie finale Bericht- und
LEG-Artefakte werden verschlüsselt verwaltet. Fachliche Dokument-ID und
physische Storage-Generation bleiben getrennt. Der produktive Backup-/Restore-
Pfad verwendet ausschließlich installationsgebundene `.jkmebackup` mit
Hauptdatenbank, Companion, notwendigen Keyset-/Envelope-Metadaten und
registrierten verschlüsselten Dokumentgenerationen, jedoch ohne DMK,
Passwörter, Recovery-Codes oder Gerätecredentials. Restore verlangt
Vollverifikation, Staging, `RESTORE_READY`, Sicherheitsbackup, separaten Worker,
kontrollierten Austausch, Reopen/Neustart und Rollback.

Der frische Pilot beginnt mit dem aktuellen Schuljahr `2026/27` vom 01.08.2026
bis 31.07.2027. Individuelle Dokumentationsfachprofile gelten pro Schüler und
Schuljahr als `inherit` oder exakte `custom`-Auswahl einschließlich bewusst
leer. Die Entwicklungsübersicht zeigt Timeline, Fachkarten und
Dokumentationsumfang für dieses aktuelle Schuljahr unabhängig von einem
Berichtsentwurf und ohne Stärke-, Schwäche-, Score-, Trend- oder
Prioritätsdeutung. Ein Bericht bleibt ein getrenntes Arbeitsprodukt mit dem
RPD-Zeitraum seines bewusst gewählten Entwurfs.

Qt bleibt Produktdefault für Bericht und LEG. Die lokalen gehärteten HTML-
Hosts hinter `JKM_REPORT_UI=html` beziehungsweise `JKM_LEG_UI=html` sind nur
interne Erprobungspfade und kein Pilotstandard. Finale RPA- und LCA-PDF-
Artefakte öffnen über denselben sicheren In-App-Viewer: UI und HTML übergeben
nur die Artifact-ID, Python löst sie über den bestehenden Managed-Document-
Lesepfad auf, und QtPdf zeigt die verifizierten Bytes nur im Speicher. Es gibt
keine Klartextdatei, OS-Öffnung, Download, Export, Drucken oder Teilen. Die
Source-Prüfung und ein Cocoa-Smoke sind erfolgt. Die Veröffentlichung des
Pilotstands ersetzt keine noch getrennt zu dokumentierende reale PO-Abnahme im
Qt-/HTML-Vergleich und begründet weder Stable-GO noch Developer-ID- oder
Notarisierungsnachweis. Support Reset ist im Cipher-
Produktpfad als reine Auth-Recovery aktiviert, jedoch nur mit intaktem
ursprünglichem Produktroot und vorhandenem installationsgebundenem DMK. Er
prüft Final V4 pre-auth vollständig, verlangt vor dem Auth-Commit ein
publiziertes und vollständig verifiziertes `.jkmebackup` und rotiert keine
Datenkeys. Geräteverlust und fehlender DMK bleiben nicht recoverbar.

0.4.0 / Build 400 bezeichnet den veröffentlichten, unveränderlichen
Pilotstand aus `e96a77e`. Seine Veröffentlichung ist getrennt von realer
macOS-/Keychain-/Restore-/UX-Abnahme, Developer ID, Notarisierung,
Stable-Freigabe, Appcast-Entscheidung und schulischer Betriebsfreigabe zu
bewerten. Keine dieser getrennten Entscheidungen wird durch diese
Dokumentation nachträglich erteilt.

## Qt-Bericht-Grundworkflow für den Pilot

Die Qt-Berichtswerkstatt ordnet den vorhandenen RPD-Arbeitsstand sichtbar in
die drei menschlichen Aufgaben `Auswählen`, `Schreiben` und
`Prüfen & finalisieren`. Ein neuer Entwurf beginnt weiterhin bei der bewussten
Fach-, Kompetenz- und Belegauswahl; ein vorhandener Entwurf öffnet ohne neue
persistierte Positionsinformation im Schreibbereich. Auswahl und Schreiben
bleiben jederzeit direkt wechselbar und bilden keinen gesperrten Assistenten.

Die vollständige Draftvorschau und die bestehende Finalisierung gehören zum
dritten Schritt. Unveränderliche RPV-Revisionen bleiben als `Frühere
Fassungen` sekundäre read-only Historie erreichbar. Die internen Qt-Routen
`writing`, `evidence`, `preview` und `revisions` bleiben für vorhandene
Deep-Links erhalten. Der sichtbare Umbau führt weder Datenquelle, Persistenz,
Schemaänderung noch neue Berichtsemantik ein.

Ungespeicherte Qt-Berichtsänderungen verwenden bei sichtbarem Schließen,
Escape und Fensterschließen denselben Drei-Wege-Vertrag: `Entwurf speichern`,
`Änderungen verwerfen` oder `Weiter bearbeiten`. Geschlossen wird nach der
Speicherwahl erst, wenn der vorhandene RPD-Speicherpfad den vollständigen Draft
erfolgreich bestätigt hat. Ein Speicherfehler lässt Workspace und Dirty-State
unverändert geöffnet.

## Intern gegatete HTML-Berichtswerkstatt

Die produktive Berichtswerkstatt kann intern mit `JKM_REPORT_UI=html` über
eine lokale qrc-/QWebEngine-Oberfläche geöffnet werden; `qt` bleibt bis zur
manuellen Abnahme der Standard. Der HTML-Host verwendet dieselben vollständigen
RPD-Drafts, Save-/Finalisierungsservices, unveränderlichen RPV-Snapshots und
opaque RPA-Referenzen wie der Qt-Host. Python bleibt Source of Truth, und die
gehärtete WebEngine-Basis wird mit dem unabhängigen LEG-HTML-Pfad geteilt.
`Finales PDF anzeigen` übergibt ausschließlich die Artifact-ID an denselben
sicheren Python- und In-Memory-Viewer-Vertrag. Die noch offene reale PO-Abnahme
im Qt-/HTML-Vergleichsbuild sowie der Bundle-/Packaging-Nachweis begründen
keine Pilot- oder Releasefreigabe.

## Cipher-Produktkomposition für Lauras Pilot

**Status:** Der normale Produktstart ist für eine frische Installation auf die
authentifizierte, verschlüsselte Final-V4-Runtime umgestellt. Verbindlich sind
`sqlcipher3 0.6.2+jkm.sqlcipher4170.1`, SQLCipher `4.17.0 community`, SQLite
`3.53.3` und CommonCrypto; eine andere oder fehlende Engine stoppt den Start
ohne Standard-SQLite-Fallback.

Nach erfolgreicher lokaler Authentifizierung lädt oder provisioniert die
Composition Root genau eine DMK-/Database-Key-Runtime, öffnet Hauptdatenbank,
Dokument-Companion und Managed Document Store keyed und injiziert dieselbe
Runtime in Repositories, `StudentDesktopAdapter` und `AppShell`. Ein echter
fachlicher First Run legt ausschließlich das aktuelle Schuljahr `2026/27`
an. Schüler, Gruppen, Kurse, Assignments, Beobachtungen und Testdaten bleiben
leer; der offizielle Kompetenzkatalog wird erst über dieselbe keyed Runtime
bereitgestellt.

Vorhandene Klartext-Fachdaten und Klartext-Dokumente werden weder geöffnet noch
migriert, umbenannt, gelöscht oder überschrieben. Ein unvollständiger
Cipher-Bestand, eine fehlende DMK, ein ungültiges Envelope oder eine fehlende
Haupt-/Companion-Datenbank werden beim Restart fail-closed abgewiesen. Die
vorhandene Datensicherungsoberfläche verwendet im Cipher-Produktmodus jetzt
ausschließlich `.jkmebackup`, vollständiges Restore-Staging,
`RESTORE_READY`, verschlüsseltes Sicherheitsbackup und den bestehenden
Cipher-Live-Worker. ZIP-v1 und V3 bleiben gesperrt. Support-Reset verwendet die
existing-only Pre-Auth-Komposition mit demselben vorhandenen DMK, vollständiger
read-only Produktprüfung und verifiziertem `.jkmebackup` vor dem bestehenden
atomaren Auth-Commit. Build, Packaging, Release und die manuelle
macOS-/UI-Abnahme sind nicht Bestandteil dieses Pakets.

## Final-V4-Fachrelevanz: veröffentlichte Basis und unveröffentlichte Dashboard-Korrektur

Final V4 ist der neue und einzige fachliche Pilot-Schemavertrag. Frische
Hauptdatenbanken werden direkt mit `PRAGMA user_version = 4` und dem exakten
V4-Fingerprint
`a3a4ec7694daf60fe90a547036f5d7573f4875800a411f923485e76582ea3516`
erzeugt. Es gibt keinen erhaltenswerten
fachlichen V3-Klartext- oder V3-Cipher-Bestand: V3 wird weder migriert noch
importiert, konvertiert, überschrieben oder gelöscht, sondern fail-closed
abgewiesen. Testdaten entstehen nach Fertigstellung neu; Laura legt ihren
realen Schülerbestand anschließend selbst an.

Die globale `documentation_subject_settings` bleibt Default. Pro
`student_id` und `school_year_id` gilt ohne Profil beziehungsweise im Modus
`inherit` dieser aktuelle globale Default. `custom` speichert eine exakte
normalisierte Fachmenge, die spätere globale Änderungen nicht verändern.
Schreiben ist ausschließlich im eindeutigen `current`-Schuljahr zulässig;
geschlossene und geplante Jahre bleiben read-only. Der Resolver verwendet
keine Stammgruppe, keinen Kurs, keine Klassenstufe, keine Beobachtungsmenge und
keinen Kompetenzstand. Fachrelevanz filtert Dokumentationsprojektionen und
löscht oder deutet keine Beobachtung, Kompetenz, Bewertung oder historische
Ausgabe um.

Cipher-First-Run, `.jkmebackup`, Restore-Staging, Restore-Worker,
Bootstrap-Recovery, Rollback und Live-Restore akzeptieren ausschließlich den
V4-Vertrag. Die eigenständige Dokument-Companion-Schemaversion 1 sowie Key-,
Envelope- und Verschlüsselungsarchitektur bleiben unverändert. Die fachliche
UI- und Projektionsintegration ist im Schülerprofil für Kompetenz-Cockpit,
Dokumentationsstatus, Profilring und neutrale Hinweise auf noch nicht
dokumentierte Bereiche umgesetzt. Laura kann für das aktuelle Schuljahr
bewusst zwischen `inherit` und einer exakten individuellen Auswahl wechseln;
historische Belege bleiben lesbar. Diese Final-V4-, Resolver- und
Schülerprofilbasis ist Bestandteil des veröffentlichten Build 400 aus
`e96a77e`. In diesem veröffentlichten Stand verwendeten Dashboard-Heatmap und
`Passende Kinder für diese Stunde` die individuelle Fachrelevanz jedoch noch
nicht korrekt für jedes Kind.

Erst der unveröffentlichte Nachfolger `926582f` korrigiert diese beiden
Dashboard-Projektionen und wertet dafür die effektive individuelle Fachmenge
je Kind aus. Diese Korrektur ist nicht Bestandteil von Build 400. Eine spätere
Veröffentlichung benötigt eine neue monotone Buildnummer von mindestens 401;
ob die sichtbare Produktversion dabei 0.4.0 oder 0.4.1 lautet, bleibt einer
gesonderten Product-Owner-Entscheidung vorbehalten. Beobachtungsdialog,
Berichtsvorbereitung und LEG folgen weiterhin ihren getrennten Verträgen.

## Historische V3-only Grundlage und Architecture Cleanup

**Status:** Durch den Final-V4-Pilotvertrag für die fachliche Schemaidentität
abgelöst. Weiterhin gültig bleiben zentrale Assignment-API,
SJ-2E-Leserumstellung, SJ-2F-Writerumstellung und die Final-V4-Runtime-
Aktivierung sowie die isolierte synthetische SJ-3C.2-Ausführung sind lokal
implementiert. Die manuelle macOS-Abnahme bleibt offen.

V3 war der erste vollständige Vorgängervertrag und ist heute nicht mehr als
Produktschema zugelassen. Seine in Final V4 fortgeführte Grundlage enthält `school_years`,
datierte `student_school_year_assignments`, `courses.year_level`,
`students` ohne `group_id` und `course_id` sowie
`school_year_transitions` ausschließlich für echte spätere
Schuljahreswechsel. Aktuelle und historische Mitgliedschaften werden nur am
expliziten fachlichen Referenzdatum aus Assignments aufgelöst.

Es existieren keine produktiven V2-Daten. Vorhandene V2-Bestände sind
synthetische Entwicklungsdaten, werden nicht migriert und dürfen für Tests
durch frisch erzeugte deterministische V3-Bestände ersetzt werden. Echte
Nutzerdaten werden erst nach vollständiger V3-Implementierung, Prüfung und
Freigabe verwendet. Es gibt keinen V2-Cutover, keinen V2-Bootstrap-Assistenten,
keinen V2-Produktrestore und keine dauerhafte V2-Kompatibilitätszusage.

Der technische Cleanup hat das bisher in der isolierten Migrationsengine
enthaltene finale DDL in `FinalV3SchemaInitializer` überführt und Engine,
Klassifizierung, Cutover-Plan, Backup-Evidence, Failpoints und
V2-Startupzustände entfernt. Compatibility, Backup und Restore akzeptieren
ausschließlich das exakte finale Schema. Das unabhängige Backupformat-v1
bleibt bestehen.

Das damalige V3-Startupziel und `V3_SCHEMA_READY` sind durch den direkten
Final-V4-First-Run und `V4_SCHEMA_READY` ersetzt. V3 wird nicht mehr zur
normalen Runtime zugelassen; unbekannte oder beschädigte Schemata bleiben
fail-closed. Nach dem V4-Gate öffnet die Composition Root die vorhandene
Datenbank ausschließlich ohne Create-Fallback; verschwindet sie, stoppt der
Start fail-closed.

Der aktuelle Cipher-Produkt-First-Run erzeugt das vollständige Final-V4-Schema,
prüft Haupt- und Companion-Datenbank keyed und legt anschließend ausschließlich
das Schuljahr `2026/27` an. Der frühere schemaisolierte Vertrag ohne Schuljahr
bleibt nur für historische Core- und Testkontexte bestehen und ist nicht mehr
der normale Pilotstart.

Implementiert sind die Qt-freien, Connection-gebundenen
`SchoolYearRepository`- und
`StudentSchoolYearAssignmentRepository`-Grenzen, der konsistente
`SchoolYearAssignmentQueryService`, das Membership-freie `V3Student`-Modell
und die isolierten Einzelkind-Lifecycles für Anlage, Stammdatenänderung,
Einschreibung, unterjährigen Wechsel, Austritt und Archivierung. Alle
Referenzdaten sind explizit; Batchreads sind set-basiert; Mehrdeutigkeit und
fehlende Zuordnung bleiben sichtbare Zustände.

SJ-2E stellt die produktiven Membership-Leser für Schülerlisten und -profil,
Gruppen, Kurse, Kursverbünde, Dashboard, Beobachtungsbearbeitung,
Berichtsvorbereitung und -finalisierung sowie LEG-Vorbereitung und -Abschluss
auf diese API um. Aktuelle Ansichten bestimmen genau ein explizites `as_of`
pro Read-Snapshot; historische Auflösung verwendet `observations.date`,
`period_end` beziehungsweise `conference_date`. Connection-gebundene
`SchoolYearAssignmentReadSession`-Komposition, zentrale Counts und
set-basierte Batchabfragen verhindern V2-Fallbacks und N+1-Reads. Report- und
LEG-Snapshotbildung einschließlich Assignmentauflösung und persistierendem
Revisionsschritt liegt jeweils in derselben Transaktion. Bestehende
Revisionen, Hashes und PDF-Artefakte werden nicht neu aufgelöst.

SJ-2F stellt die produktiven Schüler-, Kurs- und Stammgruppen-Writer auf die
in Final V4 fortgeführte V3-Stammdatenform um. Schüleranlage schreibt
Stammdaten und initiales
`enrolled`-Assignment atomar. Stammdatenänderung, datierter Einzelwechsel,
Austritt und Archivierung bleiben getrennte Lifecycles; Austritt archiviert
nicht, Archivierung verändert keine Assignments und wird bei aktueller
Einschreibung blockiert. Der bisherige generische V2-Schülercommand und die
testlokale Legacy-Membershipfixture sind entfernt.

Kurse verlangen eine bewusst gewählte stabile `year_level` von 1, 2 oder 3;
mehrere Kurse derselben Stufe bleiben zulässig. Kurs oder Stammgruppe dürfen
an einem expliziten Stichtag nicht deaktiviert werden, solange aktuelle oder
zukünftige `enrolled`-Assignments darauf verweisen. Historische Assignments
bleiben unverändert lesbar; Stammdatenwrites buchen kein Kind um.

Der synthetische Entwicklungs-/Testdatenpfad erzeugt ausschließlich frische
deterministische Final-V4-Daten mit geschlossenem Schuljahr `2025/26`,
erhaltenen historischen Assignments und genau einem current-Schuljahr
`2026/27` samt vollständigen aktuellen Assignments. Kursstufen,
V3-Schülerstammdaten und Stammgruppen bleiben konsistent. Der Pfad migriert
oder überschreibt keine vorhandene Datenbank und verwendet keine echten Daten.

SJ-3A implementiert ausschließlich die Qt-freie, rein lesende
Schuljahreswechsel-Vorschau. Sie prüft Zieljahresdaten, liest jedes V3-Kind
und dessen Assignmentkandidaten am Ende des eindeutigen current-Schuljahres,
übernimmt eine gültige aktive Stammgruppe unverändert und schlägt anhand
`courses.year_level` nur bei genau einem aktiven Zielkurs 1→2 oder 2→3 vor.
Alle ausgeschlossenen oder uneindeutigen Fälle bleiben sichtbar und
`UNRESOLVED`. SJ-3A selbst enthält keine UI, Persistenz, Aktivierung,
Authentifizierung, Backup- oder Mehrkindwechselfunktion.

SJ-3B.1 ergänzt einen isolierten rein lesenden PySide-Dialog. Er zeigt Kopf,
Zähler und jedes vorhandene Preview-Item unverändert, erlaubt nur Schließen
und besitzt weder Repository-/Write-Aufruf noch Ausführungsmöglichkeit.

SJ-3B.2a ergänzt in der Preview den ausschließlich aus V3-Schülerstammdaten
aufgelösten Anzeigenamen bei stabiler `student_id`. Ein fehlender referenzierter
Stammdatensatz bleibt neutral sichtbar und blockierend. Das neue unveränderliche
Application-Planmodell erlaubt nur rein flüchtige bewusste Kurs-, Stammgruppen-,
Wiederholungs-, Austritts- und Ungelöst-Entscheidungen. Preview, Datenbank und
ursprüngliche Issues bleiben unverändert.

SJ-3B.2b stellt genau diesen flüchtigen Plan im vorhandenen Vorschau-Dialog
individuell je Kind bearbeitbar dar. Schülername, bisherige Zuordnung,
Zielstatus, Zielgruppe, Zielkurs sowie Warnungen und Blocker bleiben sichtbar.
Jede bewusste Auswahl erzeugt eine neue Planinstanz; Planstatus und Zähler
werden daraus neu projiziert. Global ist weiterhin ausschließlich Schließen
zulässig.

SJ-3B.3 ergänzt ausschließlich flüchtige Filter, stabile Auswahl und
Sammelbearbeitung im vorhandenen Dialog. Der minimale Einstieg
`Einstellungen → Schuljahre` zeigt das aktuelle Schuljahr, nimmt Bezeichnung,
Beginn und Ende des Zieljahres entgegen und öffnet nach der vorhandenen
Preview-Validierung diesen Dialog mit einem Plan aus demselben
`query_only`-Snapshot. Ungültige Jahresdaten bleiben neutral sichtbar.

Die integrierte Oberfläche bündelt den unveränderten Funktionsumfang in zwei
reinen Präsentationsschritten: `Zuordnungen prüfen` startet bei den ungelösten
Fällen und hält alle Kinder über den Statusfilter erreichbar;
`Prüfen und aktivieren` trennt Zusammenfassung, Prüfbestätigung, Passwort und
finale Aktion räumlich vom Arbeitsbereich. Fünf kompakte Zähler bilden die
Orientierung, weitere Filter sind einklappbar und Sammelaktionen nur bei einer
sichtbaren Auswahl eingeblendet. Die read-only Tabelle und die persistenten
externen Einzelentscheidungen erhalten den macOS-Accessibility-Lifecycle.
Kleine Fenster verwenden einen vertikal scrollbar erreichbaren Arbeitsraum
mit untereinander angeordneter Liste und Detailkarte. Diese Komposition fügt
keine Plan-, ViewModel-, Persistenz-, Backup-, Step-up-, Maintenance- oder
Ausführungslogik hinzu.

SJ-3C.2 ergänzt die isolierte Qt-freie atomare Ausführungslogik auf
temporären synthetischen Final-V4-Datenbanken. Der unveränderliche Plan trägt
einen technischen Quellenfingerabdruck; sein kanonischer Plan-Hash enthält
keine Anzeigenamen. Nach `BEGIN IMMEDIATE` werden Quellen, current- und
Zieljahr, Assignments sowie Kurs-/Gruppenreferenzen erneut geprüft. Der
Service schließt das Ausgangsjahr, legt das Zieljahr als current an, schreibt
genau ein Zielassignment je Kind sowie den technischen Beleg und prüft Counts,
Constraints, Integrität und Foreign Keys vor Commit. Identische Retries sind
idempotent; jede Abweichung oder jeder Schreibfehler wird abgelehnt
beziehungsweise vollständig zurückgerollt.

SJ-3C.4 verbindet die isolierte atomare Ausführung jetzt mit dem vorhandenen
Backup-Service und dem Maintenance-Gate. Ein neuer Lauf benötigt eine echte
`SCHOOL_YEAR_TRANSITION`-Capability, vollständigen Writer-Drain und ein
veröffentlichtes, erneut verifiziertes Backup des unveränderten Quellenstands.
Der Nachweis bindet sichere technische Backup-ID, echten Archivhash,
Quellenhash, Final-V4-Fingerprint und Verifikationszeitpunkt; der persistierte
Transitionbeleg trägt den echten Archivhash. Sichere Fehler rollen vollständig
zurück und geben das Gate frei, uneindeutige Zustände bleiben
`RECOVERY_REQUIRED`.

SJ-3C.5 setzt unmittelbar vor diese geschützte Backendkette die vorhandene
App-Passwortprüfung. Nur ein vollständig gelöster Plan kann eine flüchtige,
kurzlebige, planhashgebundene Einmal-Autorisierung für
`SCHOOL_YEAR_TRANSITION` erhalten. Der Executor verbraucht sie, bevor er
Maintenance anfordert; erst danach folgen Writer-Drain, Backup und atomare
Transition. Fehlgeschlagene oder gedrosselte Authentifizierung, Ablauf,
falscher Zweck, Wiederverwendung und Abbruch bleiben vollständig vor
Maintenance und fachlichen Writes. Die Autorisierung enthält keine
Credentialdaten und wird nicht persistiert.

SJ-3C.6 verdrahtet diese bestehende Kette in der Settings-Oberfläche. Der
vollständig gelöste Plan verlangt Prüfcheckbox, App-Passwort und die
zielbenannte Aktivierung. Ein Desktop-Worker hält den Eventloop frei,
verhindert Doppelstarts und sperrt Dialog sowie App-Schließen während des
kritischen Laufs. Erfolg bestätigt Backup und Transition, zeigt
Ergebniszahlen und lädt die App-Daten neu; Fehler bleiben neutral.

Nicht Bestandteil des Schuljahreswechsels sind Planpersistenz,
Touch-ID-Freigabe und unterjährige Mehrkindwechsel. Build 400 wurde später aus
`e96a77e` veröffentlicht; aus dem aktuellen abweichenden HEAD besteht keine
neue Packaging- oder Releasefreigabe. Die reale Pilotprüfung der Runtime sowie
der Schüler-, Wechsel-, Austritts-, Kursstufen- und
Schuljahreswechseloberflächen bleibt ein eigener Abnahmestatus. Die
Implementierung selbst verwendete keine Migration und keine echten Daten.

## Schuljahresmodell und echte Wechsel

Der vollständige Schuljahreswechsel ist Bestandteil des veröffentlichten
Build 400 aus `e96a77e`. Er umfasst Vorschau, individuelle und gebündelte
Auflösung des flüchtigen Plans, Passwort-Step-up, verpflichtendes verifiziertes
Sicherheitsbackup, Maintenance-Gate, atomare Aktivierung, Rollback,
Integritätsprüfung und Übergangshistorie. Er ist keine Zukunftsfunktion und
kein vom Schülerlisten-Import abhängiger Planungskandidat. Reale Pilot- und
Betriebsabnahmen bleiben davon als eigener Status getrennt.

Die Domainmodelle `SchoolYear` und
`StudentMembershipAssignment`, ihre Datums- und Intervallinvarianten sowie
die Datenhoheit aus ADR-095 bleiben verbindlich. Ein echter späterer
Schuljahreswechsel führt von einem vorhandenen current-Schuljahr zu bewusst
festgelegten flüchtigen Zieljahresdaten. Das Zieljahr wird erst innerhalb der
atomaren Wechseltransaktion neu und als current angelegt. Sein
`school_year_transitions`-Beleg besitzt nach dem Commit immer ein vorhandenes
Ausgangs- und Zielschuljahr; eine Bootstrap-Transition mit leerer Ausgangs-ID
ist ausgeschlossen.

Vorschau, Passwort-Step-up, explizite UI-Bestätigung, Maintenance-Gate,
verifiziertes Sicherheitsbackup, erneute Quellenprüfung, atomare Transaktion,
Rollback, Idempotenz, Historie und unveränderliche finale Bericht-/LEG-
Artefakte bleiben für diesen Produktprozess erforderlich und sind bis zur
UI-Ausführung verdrahtet. Die reale Pilot-/Betriebsabnahme bleibt offen.

## Berichte-Übersicht - implementierte Phase 2

### Historische Basis: Paket 1 und Paket 1.1

Paket 1 stellt die getrennten vorhandenen Bericht- und LEG-Zustände, den
eindeutig gewählten RPD-Zeitraum, konkrete nächste Schritte, eine gemeinsame
read-only Anzeigehistorie und die Navigation in den vorhandenen
Berichtarbeitsraum bereit. Die fachlichen Aggregate und Schreibprozesse
bleiben getrennt.

Paket 1.1 verdichtet die vorhandene Übersicht visuell. Es zeigt auf Basis der
Paket-1-Projektionen eine platzbegrenzte Meilensteinleiste und kompakte
Fachkarten. Dieser historische Zwischenstand verwendete die
Paket-1-Semantik mit `documented_count/current_count`, Screen-eigener
Inhaltsbegrenzung und `orientation_changes`; Phase 2 hat diese Semantik im
Berichtsbereich vollständig ersetzt.

### Implementiert: Pakete 2A.1, 2A.2, 2B und 2C

Phase 2 ist als rein lesende Berichtsvorbereitung implementiert. Dauerhafte
Source of Truth sind die zuständigen Governance-Dokumente: Architektur in
`DECISIONS.md`, technische Begriffe in `docs/TECHNICAL_NAMES.md`,
Datenquellen in `docs/DATA_REGISTRY.md`, Projektionsablauf in
`docs/DATA_LIFECYCLE.md`, View-Verantwortung in
`docs/VIEW_DATA_OWNERSHIP.md`, sichtbare Felder in
`docs/UI_DATA_MAPPING.md` und UX in `docs/DESIGN_SYSTEM.md`.

Die Entwicklungsübersicht im Schülerprofil zeigt Timeline und Fachkarten
ausschließlich für das aktuelle Schuljahr. Sie verwendet die effektiven
Schülerfächer und ist von Berichtsentwürfen unabhängig. Die konkrete
Berichtswerkstatt beantwortet weiterhin ausschließlich, welche vorhandenen
Beobachtungen und Belege Laura im bewusst gewählten RPD-Zeitraum für den
Bericht verwenden kann. `Überblick` bleibt Eigentümer der kompakten
Lernentwicklungsdarstellung;
`Kompetenzen` bleibt Eigentümer der detaillierten Kompetenz- und Belegansicht.
Phase 2 führt deshalb weder einen neuen Themenverlauf noch einen
Kompetenzentwicklungs-Drill-down, eine dritte Lernentwicklungsdarstellung,
eine automatische Entwicklungszusammenfassung oder eine automatische
Berichtsformulierung ein.

Die Entwicklungsübersicht verwendet ausschließlich den inklusiven Zeitraum
des eindeutigen `current`-Schuljahres. Sie zeigt pro aktivem
`observation_id`, abgeschlossenem `report_draft_id`, abgeschlossenem
`learning_conference_draft_id` und aktuellem sicheren
`(student_id, competency_id)`-Bestätigungsstand höchstens ein neutrales
Timeline-Ereignis. Kompetenzzuordnungen bleiben Fachkarten- und
Beleggrundlage, erzeugen aber keine eigenen Timeline-Karten.
`persistence_events` und `orientation_changes` sind keine Timeline-Quellen.
Berichte verwenden `finalized_at` der neuesten gültigen, hashverifizierten
Revision; LEG verwendet `conference_date`, nicht `completed_at`.

Fachkarten zeigen absolute Dokumentationsmengen ohne Nenner, x/y-Semantik,
Prozentwert, Restspur oder Bewertung. Kleine fachbezogene Symbole unterstützen
die Orientierung, ohne eine fachliche Wertung oder ein Diagramm zu bilden.
Historische Kompetenzen bleiben aus aktuellen
Zählern ausgeschlossen. Bericht und LEG bleiben getrennte Aggregate und
werden nur displayseitig gemeinsam angezeigt. Die Timeline ist
ereignisorientiert und enthält weder Trend, Entwicklungsrichtung,
pädagogische Priorisierung noch Stärke-, Defizit- oder Förderlogik.

Die Implementierung ergänzt reine ViewModel-Projektionen, schülerbezogene
SQLite-Read-Snapshots, getrennte Batch-Lesepfade für Bericht- und
LEG-Revisionen, absolute Fachkarten und die horizontale
Dokumentations-Timeline. Sie ergänzt keine Tabelle, Migration, Schreiblogik
oder Persistenz. Automatisierte Offscreen-Tests prüfen die 2/4/5-Viewport-
Kapazitäten, Scrollsteuerung, Tastatur, Ankererhalt und ID-Navigation. Reale
macOS-Trackpad- und VoiceOver-Abnahme bleibt offen. Im damaligen
Phase-2-Implementierungspaket wurden Build, Packaging, Push, Tag und Release
nicht ausgeführt; die Funktion wurde später Bestandteil von Build 400.

## Berichte-Übersicht 0.3.1 / Build-304-Scope - Paket 1

Paket 1 ersetzt die bisherige vorbereitende Berichtsvorschau im Register
`Bericht` des Schülerprofils durch eine vertikal scrollbare, read-only
orchestrierte Übersicht. Sie zeigt Bericht-, LEG- und nächste Statusschritte,
den ausschließlich aus einem eindeutig gewählten RPD stammenden
Berichtszeitraum, eine gemeinsame Anzeigehistorie und Fachsprunganker.

Bericht und LEG bleiben technisch und fachlich getrennt. Ihre vorhandenen
Draft-, Revisions-, Abschluss- und Integritätsprojektionen werden erst im
Desktop-Adapter zu einer displayfertigen Übersicht zusammengesetzt. Bei
mehreren Berichtsentwürfen oder LEG-Arbeitsständen wird niemals automatisch
gewählt; `Zuletzt bearbeitet` beeinflusst nur die Reihenfolge der bestehenden
Auswahl.

Der bestehende `LearningReportDialog` bleibt in Paket 1 der einzige
Berichteditor. Die Übersicht öffnet ihn über eine kontrollierte
Navigationsgrenze und kann dort den vorhandenen Bereich
`Kompetenzen & Belege` sowie ein Fach fokussieren. Eine Einbettung als
gemeinsamer `LearningReportWorkspace` bleibt einem späteren Paket vorbehalten;
Editorzustand, Speichern, Revisionen, Vorschau und PDF-Funktionen werden nicht
dupliziert.

Zeitleiste, Stärken-/Watch-Kandidaten, neue Kompetenzlogik, neue Persistenz,
Migration und Schuljahresmodell gehören nicht zu Paket 1. Die entsprechenden
Flächen sind neutrale, klar bezeichnete Leerzustände.

## Pilot-Releaseautomation

Der mit Build 303 nachgewiesene lokale Pilot-Releaseprozess ist als
terminale, wiederaufnehmbare Automation umgesetzt. Build 303 bleibt seit
27. Juli 2026 die konfigurierte historische Appcast-Regressionsreferenz:
GitHub-Pre-Release
`v0.3.0-build303`, Quellcommit
`07c20a3764405bc1f535eb33efe809519dd8316b` und aktiver Pilot-Appcast. Stable
bleibt deaktiviert. Der spätere veröffentlichte Build 400 ist davon getrennt
die aktuelle unveränderliche Pilot-Quellreferenz; sein Appcast-Status wird
nicht aus der Build-303-Konfiguration abgeleitet.

`scripts/release_pilot.py` trennt Inspect, Prepare, detached Clean-Build,
Paketprüfung, GitHub-Draft/Assetverifikation, Appcast-Publikation und
öffentliche Endverifikation. Das monotone Manifest ermöglicht sichere
Wiederaufnahme ohne Neubau nach späteren Netzwerk- oder
Authentifizierungsfehlern. Version und Build werden nie automatisch geändert;
Veröffentlichungen benötigen getrennte explizite Gates. Architektur,
Sicherheitsgrenzen und Betrieb stehen in `docs/RELEASE_AUTOMATION.md`.

Die Automation verändert weder Produktlogik noch SQLite-Datenmodell, UI,
Backup-/Restoreformat oder Verschlüsselungsstatus. Sie enthält keine Secrets,
liest keinen privaten Sparkle-Schlüssel und kann Stable weder erzeugen noch
aktivieren.

## Historischer Vorbereitungsstand 0.3.0 / Build 303

Der folgende Abschnitt hält den dokumentierten Stand vor der späteren
Veröffentlichung fest. Build 303 war zu diesem Zeitpunkt ein
macOS-arm64-Vorbereitungsstand, kein Release Candidate und kein verteiltetes
Artefakt. Der race-freie
Restore-Neustartfix ist committed. Die verbindliche Produktwahrheit, offene
Artefaktnachweise und Releasegrenzen stehen in
`docs/SECURITY_RELEASE_0_3_0.md`; die verständliche Schutzdarstellung in
`docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md`.

`src.version` führt `0.3.0` / Build `303` als gemeinsame Quelle für Bundle,
Über-Dialog, Buildkonfiguration und Dokumentgenerator. Der normale Gate-Off-
Pfad bleibt lokale SQLite-Datenbank, verwaltete Klartextdokumente und
ZIP-v1-Backup/Restore. Nur interne markergebundene Pakettests laden SQLCipher,
PyNaCl/libsodium und den Integrationsorchestrator. Es gibt keine automatische
Migration, keine UI-Aktivierung und keinen Zugriff auf Pilot- oder
Produktdaten.

Der macOS-arm64-Build verwendet ein neues Venv mit exakt gepinnten Versionen,
prüft native Laufzeiten vor PyInstaller, reduziert das fertige Bundle auf
arm64, signiert erst danach und führt Gate-Off-, Gate-On-, Keychain-, Bundle-,
Artefakt-, Pfad- und Klartextprüfungen vor DMG-Erzeugung aus. SQLCipher
Community 4.12.0 bleibt ausdrücklich nur die Sprint-11-Testengine; das
SQLCipher-4.17.0-Produktziel ist nicht freigegeben.

Builds 300 bis 302 bleiben historische, nicht verteilte Ausgangsstände.
Build 303 bündelt die dokumentierte Produktbasis einschließlich
Performance-Batch, Kursverbundsnapshot, Ereignisordnung,
Attachment-Unit-of-Work, Entwurfsauswahl, Restore-Worker und UX-Hardening.
Der immutabel nachweisende App-, DMG- und Prüfsummenstand wird ausschließlich
aus dem noch ausstehenden finalen Clean-Build-Commit erzeugt und im Release-
Inventar festgehalten.

Windows, Developer ID, Notarisierung, physische Touch ID, vollständiger
Power-Loss-Nachweis, Produktmigration, Pilotaktivierung und Stable-Appcast
bleiben getrennte Gates. Der GitHub-Pre-Release/Pilot erfolgt erst nach
Clean-Build und vollständiger Paketabnahme; es gibt keinen Stable-Appcast und
keinen automatischen Pilotrollout.

## Final-V4-SQLCipher-Runtime - interner gated Produktstack-Smoke

Der vorhandene DMK-/Database-Key-Bestand kann nun ausschließlich hinter einem
zusätzlichen, standardmäßig inaktiven Gate und einem zweiten festen Marker im
privaten System-Temporärroot mit einer frischen Final-V4-SQLCipher-Datenbank
verbunden werden. Der Pfad verlangt bestätigte Authentifizierung und bei einer
Neuanlage eine explizite technische First-Run-Bestätigung. Er verwendet exakt
das lokale Binding `0.6.2+jkm.sqlcipher4170.1`, SQLCipher
`4.17.0 community`, CommonCrypto und SQLite `3.53.3`; der getrennte 4.12-Pfad
und der damalige SQLite-Produktdefault blieben in diesem Foundation-Paket
unverändert. ADR-101 aktiviert die exakte 4.17-Runtime inzwischen für den
frischen Pilot-Produktstart.

Schemaerzeugung, keyed Kompatibilitätsprüfung und die an Repositories sowie
Desktop-Adapter übergebene `SQLiteDatabase` teilen dieselbe feste
Provider-/Database-Key-Konfiguration. Restart öffnet zunächst read-only keyed
und prüft Cipher, Integrität, Foreign Keys, Final-V4-Version und vollständigen
Fingerprint. Fehlende oder widersprüchliche Schlüssel-/DB-Bestände,
Klartext, falsche Keys, unbekannte Versionen, Crashreste und unvollständige
Schemata blockieren ohne Migration, Reparatur oder stille Neuerzeugung.
Gate, Marker und exakt abgeleitete Pfade werden an Coordinator und Factory
erneut geprüft; ein symlinked Runtime-Root wird abgewiesen. Fünf abrupte
Subprozessabbrüche belegen den Restartvertrag ohne kontrolliertes Unwinding.

Der technische Anwendungssmoke reicht bis zu vorhandenen Repositories,
`StudentDesktopAdapter`, `MasterDataDesktopAdapter` und einer
ViewModel-Projektion. Es gibt keine Shell-, UI-, Pilot-, Dokument-,
Backup/Restore-, Support-Reset-, Build-, DMG- oder Releaseaktivierung.

## Final-V3-Dokumentcontainer-Runtime - intern gegatete technische Grenze

Unter exakt demselben DMK-/Final-V4-SQLCipher-Gate kann eine separate
`documents-v1.sqlcipher`-Companion-Datenbank geöffnet werden. Sie besitzt eine
eigene exakte Schemaidentität und ist an dieselbe Installation, denselben
Database-Context und denselben vorhandenen Database-Key gebunden. Dadurch
bleiben Companion-Schema, Containerformat und deren unabhängiger
`FinalV3DocumentSchemaV1`-Fingerprint unverändert; die Hauptdatenbank ist
`final-v4.sqlcipher` mit `user_version=4` und Final-V4-Hauptfingerprint.

Der verwaltete Storage liegt ausschließlich im privaten Runtime-Root und
akzeptiert als Containerdateien nur `<opaque-storage-id>.jkmedoc`. Der
Qt-freie Ablauf erzeugt pro Generation einen zufälligen Document-Key, schreibt
und verifiziert den XChaCha20-Poly1305-Container vollständig, persistiert erst
danach `PREPARED` und schaltet den aktiven SQLCipher-Pointer atomar um. Der
Reader gibt Klartext nur an einen injizierten Consumer und meldet erst nach
vollständiger zweiter Final-/EOF-/Hashprüfung Erfolg. Alte Generationen bleiben
`RETAINED`; physisches Löschen findet nicht statt.

Die Runtime ist über den gemeinsamen `ManagedDocumentStore` sowohl an die
`ObservationPersistenceUnitOfWork` als auch an den kleinen journalisierten
`ManagedStudentDocumentService` für allgemeine Schülerdokumente gebunden. Die
vorhandene MED-ID bleibt Document-ID; Generation und opaque Storage-ID bleiben
rein physisch. Beide Lifecycle schreiben die fachliche Final-V4-Referenz erst
nach Vollverifikation und aktivieren danach idempotent den Companion-Pointer.
Replace behält MED-ID und alten lesbaren Stand bis zum erfolgreichen Wechsel;
Remove deaktiviert fachlich und behält alle Container retained.

Der Pilotweg setzt einen frischen verschlüsselten Final-V4-Bestand voraus.
Klartextbestände und alte Testdaten werden nicht migriert oder konvertiert;
Testdaten werden nach Gate-Aktivierung neu erzeugt. Gate-Off bleibt
unverändert. Es gibt keinen Export, OS-Preview, Produktstartup, Build oder
Releasepfad.

## Verschlüsseltes Final-V4-Pilotbackup und Restore-Staging

Der Cipher-Produktpfad sichert ausschließlich frische
verschlüsselte Final-V4-Installationen in `.jkmebackup`. Der gemeinsame
Writer-Lock friert Hauptdatenbank, Companion-DB, aktives Fachinventar und alle
registrierten Dokumentgenerationen ein. SQLCipher-Backup-Snapshots,
Keyset-Metadaten, die geschützte Database-Key-Envelope-Registry und sämtliche
`.jkmedoc`-Container werden durch ein verschlüsseltes Manifest mit Context-,
Generations-, Rollen-, Versions-, Größen- und Hashbindungen zusammengehalten.

Der Backup-Key ist zufällig und wird unter einem eigenen DMK-abgeleiteten
Backup-Wrapping-Key geschützt. DMK, Database-Key, Document-Keys,
`security.sqlite`, Passwort-, Recovery-, Device- und Keychain-Secrets werden
nicht in den Container geschrieben. Vollständige Secretstream-Verifikation,
Final-Tag und physisches EOF sind Voraussetzung für die no-clobber
Veröffentlichung.

Restore schreibt ausschließlich in einen neuen privaten Staging-Root und
bestätigt erst nach keyed Reopen beider Datenbanken, exakter SQLCipher-4.17-
und Schemaprüfung, vollständigem Dokumentinventar und Crossbindings
`RESTORE_READY`. Das Staging selbst führt keinen Live-Swap aus; dessen
technischer Konsum ist im folgenden Workerpfad getrennt geregelt. Der Vertrag ist
`same-installation encrypted restore`: Der passende DMK muss im vorhandenen
Keychain existieren; DMK-Verlust und Gerätewechsel sind nicht gelöst.
Historische Klartext-/ZIP-v1-Bestände werden nicht migriert. Gate-Off behält
bis zur Produktaktivierung unverändert ZIP-v1; die bestehende Oberfläche ist
nicht auf den neuen Pfad geschaltet.

## Verschlüsselter Final-V4-Live-Restore - technischer Workerpfad

Ein bereits vollständig verifiziertes `RESTORE_READY` kann auf Basis der
Cipher-Produktkomposition aus ADR-101 über den vorhandenen Restore-Worker live
eingesetzt werden. Vor dem
Handoff bleibt der Livebestand im Maintenance-Gate eingefroren, bis ein neues
verschlüsseltes Safety-`.jkmebackup` erstellt und vollständig neu verifiziert
ist. Der DMK-authentisierte Handoff bindet Safety-Backup, READY, Manifest,
Installation und Database-Context; der Worker bestätigt Parent-EOF, prüft
beide Nachweise erneut und verwendet das bestehende Write-ahead-Journal.

Ausgetauscht werden als eine zusammengehörige Einheit ausschließlich
`security-key-runtime-v1/`, Haupt-DB, Companion-DB und verschlüsselter
Dokumentbestand. Der alte
Bestand bleibt unter `rollback/`; kein physisches GC findet statt. Erfolg wird
erst nach frischem keyed Reopen von Haupt- und Companion-DB, vollständigem
`.jkmedoc`-Inventar, Final-V4-/Companion-Fingerprint und allen Dokument-/RPA-/
LCA-Crossbindings bestätigt. Ein Fehler rollt beide Komponenten zurück und
prüft den alten Bestand keyed; ein uneindeutiger Mischzustand wird
`manual_recovery_required`. Ein Kaltstart stellt vor jedem Product-Open nur
aus Security-/Installationskontext, bestehendem DMK, Handoff, Journal sowie
Live-/Rollback-/Staging-Rollen einen eindeutigen Gesamtbestand her.

`security.sqlite`, Keychain-DMK, Passwort-/Recovery-/Device-/Touch-ID-Daten und
`app-preferences.json` bleiben unverändert. Der Pfad ist weiterhin ausschließlich
same-installation; Geräte- oder DMK-Verlust, Klartext-/V2-/ZIP-v1-Migration und
portable Backups sind ungelöst beziehungsweise ausgeschlossen. Die bestehende
Restore-UI ist jetzt ausschließlich an diesen Cipher-Vertrag gebunden. Nach
erfolgreichem Restore-Commit läuft der frische Prozess über den regulären
Security-/Auth- und einzigen Cipher-Produktstartup weiter.

## Security Sprint 11 - kontrollierte Integration hinter inaktivem Gate

Security Sprint 11 verbindet die isolierten Foundations aus Sprint 8 bis 10
ausschließlich in einer markergebundenen temporären Testinstallation. Das
interne Gate `JKM_SECURITY_INTEGRATION_TEST=1` ist standardmäßig aus, nicht
über die UI erreichbar und akzeptiert weder den normalen `RuntimePaths`-Root
noch Pilot-, RC- oder echte Nutzerdaten. Unbekannte Gatewerte und gemischte
Bestände blockieren ohne SQLite-/SQLCipher-Fallback.

### Verbindliche Integrationsmatrix

| Komponente | historischer Klartextpfad | verschlüsselter Sprint-11-Testpfad | Gate | Fehler / Recovery | Schema | Testnachweis |
|---|---|---|---|---|---|---|
| Startup / `RuntimePaths` | normale Rootauflösung und `prepare_runtime_storage` | `SecurityIntegrationGate` plus feste temporäre `SecurityIntegrationPaths` | exakt `1` und zwei Marker | ungültiger Root blockiert vor Mutation | nein | Gate-/Import-/Startup-Isolation |
| Connection Factory | `SQLiteDatabase` über SQLite-Provider | explizite SQLCipher-Factory mit DMK-geöffnetem Database-Key | nur Integrationsruntime | falscher/fehlender Key, Format oder Integrität blockiert; kein Create-Fallback | `user_version=1101` | Open, falscher Key, Reopen |
| Auth / DMK | bestehende lokale Authentifizierung | injizierter DMK-Loader erst nach Auth-Erfolg | keine UI-Aktivierung | fehlender/beschädigter Plattformschlüssel blockiert | nein | Passwortwechsel-/Support-Reset-Semantik |
| Migration / Journal / Lock | keine automatische Produktmigration | geschlossene markierte Testquelle, byte-identische Safety Copy, SQLCipher-Ziel, HMAC-Journal, externer pending/committed Anchor und exklusiver Lock | nur Test-Root | neue Prozess-Recovery, idempotente Phasen, Widerspruch blockiert | Integrationsmetadaten v1 | Fokus- und echte Crash-Subprozesse |
| Dokumentrepository | `documents.file_path` auf Klartextdatei | unveränderliche `security_document_generations` plus opaque aktive Referenz | nur SQLCipher-Ziel | vorbereitete Generation bleibt inaktiv; alte aktive Generation retained | neue Tabellen / Index | Import, Austausch, Restart, gemischter Zustand |
| Import / Lesen / Export / Löschen | Kopie in `documents/`, direktes OS-Öffnen, Soft-Delete | Container vor Pointer, zweiphasiger Reader, bewusster No-Clobber-Klartextexport, konservatives Retained | nur Application Adapter | keine erfolgreiche Meldung bei Teilfehler; kein GC | Generation/Lifecycle | Container-, Export- und Crashtests |
| Backup / Restore | ZIP-v1 und bestehendes Restore-Handoff | Sprint-9-Container für SQLCipher plus verschlüsselte Dokumente; Restore nur in neuen Staging-Root | nur Integrationsadapter | Vollverifikation vor Erfolg; alter Bestand bleibt | nein | Tamper, Crash, Restore-Reopen |
| Application Services | historische Desktop-Adapter mit Klartext-DB | Qt-freie `SecurityIntegrationRuntime` gegen zentrale Factory | nur Testcode | sanitierte Fehlercodes; keine UI | nutzt v1 | Student-/Dokumentprojektion gegen SQLCipher |
| Support-Reset / Passwortwechsel | bestehende Auth-Schicht | unverändert; DMK-/Datenkeys bleiben identisch | unabhängig vom Gate | fehlender Plattform-DMK blockiert | nein | explizite Nicht-Rotations-Regression |
| Nutzerführung | bestehende Dialoge | keine neue UI; ausschließlich technischer Testreport | nicht sichtbar | fail-closed ohne Geheimnisse/Pfade in Logs | nein | UI-/Import-Isolation |
| Packaging | bestehende Abhängigkeiten | keine Sprint-11-Paketaktivierung | gesperrt | PyNaCl/SQLCipher-Packaging bleibt Release-Gate | nein | `pip check`; kein Build |

### Datenfluss Startup bis Restore

`Gate/Marker prüfen -> Auth bestätigt -> DMK laden -> Database-Key-Envelope
öffnen -> Locks erwerben -> Klartextquelle und Dokumentinventar binden ->
byte-identische Safety Copy verifizieren -> separate SQLCipher-Datei ohne
ATTACH übertragen und reopen -> Dokumentcontainer PREPARED erzeugen ->
SQLCipher-Referenzen atomar ACTIVE schalten -> verschlüsseltes Backup
verifizieren -> alle Handles schließen -> SQLCipher und Dokumente frisch
reopen -> Klartextbestand Retained markieren -> COMPLETED -> optional Backup in
neuen Restore-Staging-Root extrahieren und vollständig reopen-verifizieren`.

Der Klartextbestand wird nicht ersetzt oder gelöscht. Der Testpfad startet
seine Application Services direkt gegen den validierten SQLCipher-Bestand.
Für diesen historischen Sprint-11-Vertrag blieben ZIP-v1-Backup, normale
Dokumentpfade und Produktstartup unverändert. ADR-101 ersetzt diese Aussage
für den heutigen Cipher-Produktstart; Packaging und Release bleiben offen.

## Security Sprint 9 - isolierter verschlüsselter Backupcontainer

Der Sprint ergänzt ausschließlich für synthetische Testdaten einen
versionierten, authentifizierten und streamend verschlüsselten Backupcontainer.
Der bestehende `.jkmbackup`-Writer, dessen Restore-Staging, Startup, Login, UI
und RuntimePaths bleiben unverändert und importieren den neuen Pfad nicht.

Jeder Container verwendet einen zufälligen 256-Bit-Backup-Key. DMK,
HKDF-zweckgetrennter Backup-Wrapping-Key und AES-256-GCM-Envelope schützen den
Schlüssel; Manifest und Nutzdaten werden mit Secretstream XChaCha20-Poly1305
authentifiziert verschlüsselt.

Writer, Verifier und Restore-Prototyp prüfen und veröffentlichen ausschließlich
im privaten synthetischen Test-Root. Packaging, Windows, realer Power-Loss,
Same-User-ABA, Retained-GC, weitergehende Zeroization und Produktintegration
bleiben Folge-Gates; P0 = 0 und P1 = 0 im ADR-088-Bedrohungsmodell.

## Security Sprint 7B - Migration State Foundations

Security Sprint 7B ergänzt drei Qt-freie Security-Foundations: eine
HMAC-authentisierte append-only Lock-Transitionskette, einen vollständigen
kanonischen Migrations-Crossbinding-Kontext und eine deterministische
recovery-aware Preflight-Ableitung.

Crossbinding umfasst Installation, Datenbankkontext, Migration und Generation,
DMK und Database-Key, Registry, Journal, Replay-Anker, Lockkopf, Source,
Backup, Target, Capabilities, Dateiidentitäten und erwartete Engine- sowie
Schemaversionen. Der Preflight besitzt genau die Modi `NEW`, `RESUME`,
`RECOVERY`, `COMPLETED` und `BLOCKED`.

Die Foundations bleiben ohne Produkt-, Startup-, Login-, UI-, Backup/Restore-
oder Orchestratorintegration. Nachgelagerte Security-Sprints bleiben gesperrt.

## Security Sprint 6 - Replay-Schutz, exklusiver Lock und Prototype-Recovery

Security Sprint 6 ist als Erweiterung der nicht produktiv aktivierten
Foundations implementiert und nach dem P1-Fix vollständig gegatet: ein externer monotoner
Replay-Anker, ein exklusiver POSIX/macOS-Migrations-Lock und eine eng
allowlistete ausführende Recovery-Orchestrierung für den guarded synthetischen
Migrationsprototyp. Alle Abhängigkeiten werden
explizit injiziert; es gibt weiterhin keine `RuntimePaths`-, Startup-, UI-,
Login-, Backup/Restore- oder Produktkopplung.

Der Anchor-Zustand liegt außerhalb von Envelope-Registry und Journal und bindet
Installation/Security-Context, Anchor-Version/-Revision, Database-Context,
DMK-/Keyset-ID/-Generation, Registry-High-Water-Mark,
Journal-/Migrationsgeneration sowie die exakten SHA-256-Digests beider
authentisierten Dateien. macOS verwendet
den eigenen Keychain-Service
`de.jenaplan.kompetenzmanager.monotonic-security-anchor` ohne Datei-Fallback.
Ein fehlender oder beschädigter Anker bei vorhandenem Security-Bestand,
Rollback, doppelte Revision, unplausibler Sprung, Kontextabweichung und
Parallelitätskonflikt blockieren ohne stille Neuerzeugung. Ein
`committed`/`pending`-Protokoll koppelt Plattformstore und Dateipublikation:
Prepare bindet alten und exakt geplanten neuen Snapshot, Publish schreibt die
Dateien und Commit akzeptiert ausschließlich exakt pending Digests. Nach Crash
darf exakt der alte Stand durch
`abort_pending(expected, observed_committed)` monoton verworfen oder exakt der
neue Stand durch Commit aufgelöst werden; jeder Mischstand blockiert. Der
exklusive Lock serialisiert diesen Advance prozessübergreifend. Windows bleibt
auf Port, Fake, Fehlervertrag und DPAPI-user-scope-Entwurf begrenzt.

Der Plattformvertrag `MigrationLockPort` besitzt den threadsicheren Test-Fake
`InMemoryMigrationLock`, den fail-closed Adapter
`UnsupportedMigrationLock` und den POSIX/macOS-Prototyp
`ExclusiveMigrationLock`. `database-migration-v1.lock` wird im injizierten
Test-Root exklusiv angelegt.
Eigentum bindet mehr als eine PID: Installation, Datenbankkontext,
Migration-ID, Prozessstartidentität, Nonce, Erstellungszeit und Dateiidentität
werden geprüft. Fremde, manipulierte, ausgetauschte oder uneindeutig stale
Locks werden nicht automatisch gelöscht oder überschrieben.

Die ausführende Recovery prüft vor jedem Schritt Lock, Journal-HMAC,
Replay-Anker, Rootgrenze und Dateiidentität. Sie darf nur eigene
identitätsgebundene Testziele zurückrollen, Backup-/Zielvalidierung fortsetzen,
das Testziel neu öffnen und bei authentisiertem `COMPLETED` ausschließlich das
evidence-gebundene Testziel und Backup per atomarem No-Clobber-Rename in retained Quarantine
verschieben und dort idempotent identitätsprüfen, aber niemals löschen.
Klartextquelle, Anchor, Registry, Journal, Lock, unbekannte Dateien, produktive
Pfade und reservierte Swap-Phasen bleiben unverändert. Auth-Recovery-Codes und
Support-Reset sind nicht Teil dieser Recovery.

Echte Subprozessabbrüche und kontrollierte Fehleradapter decken Crashfenster,
ENOSPC, Rechte, `fsync`, Rename/Replace und Dateiwechsel ab. Der Nachweis gilt nur
für synthetische temporäre Testdaten; vollständige Power-Loss-Sicherheit bleibt
ein offenes Plattformgate. Recovery verwendet für Ziel und Backup kein
pathname-basiertes `unlink` oder `remove`; das frühere finale Unlink-TOCTOU ist
beseitigt. Ein konkurrierend angelegter Quarantänepfad wird durch
`RENAME_EXCL`/`RENAME_NOREPLACE` niemals überschrieben; fehlt dieser
No-Clobber-Primitive, blockiert Recovery. Die bekannte P2-Grenze ist retained Quarantine ohne freigegebenen
handlebasierten Bereinigungsprozess.

Das Post-Fix-Gate ist vollständig grün: 215 fokussierte Sprint-6-Tests, 265
fokussierte Tests der Security Sprints 2 bis 6, 465
Security-/Support-Regressionstests, 130 Backup-/Restore-Regressionstests sowie
die Gesamtsuite mit 1148 Tests und 67 Subtests. `compileall`, `pip check`,
`git diff --check`, native Bridge-Checks mit ausschließlich erwarteten
Deprecated-Warnungen und die geschützten Hashprüfungen waren erfolgreich;
P0 = 0 und P1 = 0. Daraus folgt keine Produktfreigabe.

Für den kontrollierten Laura-Einzelpiloten bleibt der ad-hoc-signierte,
persönlich übergebene Pfad mit reproduzierbarem Clean Build, SHA-256-Manifest,
dokumentierter Gatekeeper-Freigabe und realer Keychain-/Bundle-ID-Prüfung
zulässig. Er ist nicht notarisiert und behauptet keine verifizierte
Entwickleridentität. Breite Verteilung bleibt an Developer ID und
Notarisierung oder eine gesonderte schulinterne MDM-Entscheidung gebunden.
Security Sprint 6 baut oder verändert kein RC- oder Pilotartefakt.

Security Sprint 7A ist nicht Bestandteil dieses Commits. Security Sprint 8A
wurde nicht begonnen und bleibt gesperrt; der historische fachliche
`Sprint 8A - Produktiver Stundenplan` ist davon verschieden.

## Security Sprint 5 - Product-Key-Envelope und Migrationsjournal-Foundation

Security Sprint 5 ergänzt zwei strikt isolierte, Qt-freie Bausteine. Ein
zufälliger 256-Bit-Database-Key wird unter einem per HKDF-SHA-256 eindeutig vom
DMK abgeleiteten Database-Wrapping-Key mit AES-256-GCM geschützt. Ein eigenes
versioniertes `DatabaseKeyEnvelope` authentifiziert sämtliche öffentlichen
Metadaten einschließlich einer monotonen Rewrap-Revision als AAD und wird atomar in
`database-key-envelopes-v1.json` gespeichert. Das generische Sprint-2-
`KeyEnvelope`, der DMK-Keychain-Lifecycle und `data-keysets.sqlite` bleiben
unverändert. Eine weitere getrennte HKDF-Domain authentifiziert die komplette
Registry samt Context, Generations-High-Water-Mark und Envelope-Mitgliedschaft
mit HMAC-SHA-256; auch die leere Registry bleibt dadurch manipulationsgeschützt.

Das Migrationsjournal `database-migration-journal-v1.json` speichert nur
technische Rollen, Dateibeweise, Phasen, Checks und sanitierte Fehlerklassen.
Ein separater HKDF-Zweck authentifiziert die vollständige kanonische Datei mit
HMAC-SHA-256. Journal und Envelope sind über Database-Context sowie
Database-Key-ID/-Generation kreuzgebunden. Die explizite State-Machine
verhindert illegale Sprünge; reservierte Pflichtchecks sind an ihre erreichte
Phase gebunden und Journalzeitpunkte monoton.
Recovery prüft Quelle, Backup und Ziel erneut und liefert ausschließlich eine
technische Entscheidung. Sie führt keine Dateioperation aus. Manipulation,
Korruption, unbekannte Version, Temp-Rest, fehlende oder ausgetauschte Datei
und widersprüchliche Historie blockieren.

Der vorhandene Sprint-4-Prototyp nutzt beide Bausteine ausschließlich mit neu
erzeugter guarded synthetischer SQLite in einem temporären Root. Er beweist
Envelope-Persistenz/-Entschlüsselung, SQLCipher-Erzeugung mit dem geladenen
Database-Key, phasenweises Journal sowie eindeutige Entscheidungen nach
Abbruch hinter Backup, während/nach Export, während Validierung und nach
Neuöffnung. Ein zweiter Lauf überschreibt vorhandene Sidecars oder Artefakte
nicht.

Threat Model und Grenzen: AEAD/HMAC schützen gegen Lesen des Database-Key und
gegen Manipulation ohne DMK. Sie schützen nicht gegen einen kompromittierten
Prozess mit DMK-Zugriff, vollständiges Replay eines älteren gültigen
Envelope/Journals, physische SSD-Restdaten oder ein kompromittiertes
Betriebssystem. Die Registry besitzt einen lokalen Generations-High-Water-Mark;
ein extern gegen Rollback geschützter monotoner Anker, produktive Database-Context-Bindung,
Windows-DPAPI/ACL/File-ID/Reparse-Point-Schutz, macOS-`F_FULLFSYNC`,
kontrollierter SQLCipher-4.17.0-Build, Packaging, Signierung, reale Crashtests,
exklusiver Prozess-Lock/handlegebundene Dateioperationen, Startup-Recovery,
Rotation und sichere Klartextentsorgung bleiben offen.

Es gibt keine RuntimePaths-, Startup-, Login-, Passwort-, UI-,
Backup/Restore-, Support-Reset-, Recovery-Code-, Produktdaten-, Dokument-,
Pilot-, RC-, Appcast- oder Releaseintegration. Normales SQLite bleibt der
Produktstandard. RC `0.2.2`, `security.sqlite`, Pilotdaten und bekannte
Exceldatei werden nicht geöffnet oder verändert.

## Security Sprint 4 - isolierter Datenbankmigrationsprototyp

Security Sprint 4 weist ausschließlich mit neu erzeugten synthetischen Daten
nach, dass eine Klartext-SQLite-Datenbank kontrolliert in eine separate
SQLCipher-Datenbank übertragen und vollständig verglichen werden kann. Der
Prototyp liegt unter `prototypes/database_encryption_migration/`, besitzt keine
RuntimePaths-, Startup-, UI-, Login-, Recovery-, Support-Reset-, Backup/Restore-
oder Releaseintegration und akzeptiert nur eine technische Synthetic-Guard-
Fixture im eigenen temporären Arbeitsbereich.

Der Ablauf prüft die Quelle, erzeugt und prüft ein unverändertes SQLite-Backup,
exportiert Schema und Daten in ein separates Cipher-Ziel, stellt die von
`sqlcipher_export` nicht übertragenen persistenten PRAGMAs explizit wieder her
und vergleicht Tabellen, Zeilenzahlen, Primär-/Fremdschlüssel, Trigger, Views,
Indizes, `sqlite_sequence`, Schemahash, kanonische Datenhashes und PRAGMAs.
Danach folgen
SQLCipher-/SQLite-Integrität und ein echtes Neuöffnen. Backup-, Export-,
Commit-, Abbruch-, Korruptions-, Wrong-Key- und Versionsfehler lassen die
Quelle bytegleich und entfernen ein eigenes fehlgeschlagenes Ziel.

Der flüchtige 256-Bit-Testkey bildet nur den zukünftigen Database-Key ab. Das
Produktziel bleibt eine zufällige DB-Key-Instanz unter einem zweckgebundenen,
aus dem DMK abgeleiteten Wrapping-Key; der DMK selbst wird nie SQLCipher-Key.
Key-Wrapping, Live-Dateiaustausch, Startup-Recovery, Klartextentsorgung,
produktive Migration, Packaging und Rollout bleiben offen. RC `0.2.2`,
`security.sqlite`, Pilotdaten, Produktdaten, Backups, Dokumente und die bekannte
Excel-Datei bleiben außerhalb des Prototyps.

## Security Sprint 3 - SQLCipher Infrastructure

Eine kleine Qt-freie Engine-Grenze stellt Standard-SQLite und einen expliziten
SQLCipher-Provider bereit. Die bestehende Hauptanwendung verwendet weiterhin
ausschließlich normales SQLite; SQLCipher wird weder beim Start noch über
Login, UI, Recovery, Support-Reset, Backup oder Restore aktiviert.

Der isolierte Testpfad verwendet `sqlcipher3` 0.6.2 mit der nachgewiesenen
SQLCipher Community Engine 4.12.0, erzeugt ausschließlich temporäre
verschlüsselte Datenbanken mit synthetischen Daten und Laufzeitschlüsseln und
prüft richtiges/falsches Keying, Korruption, Integrität, Transaktionen und die
Ablehnung durch normales `sqlite3`. Ein eigenständiger macOS-arm64-
PyInstaller-Prototyp wurde außerhalb der Releasepfade erfolgreich ausgeführt.
Dieser damalige lokale Nachweis besaß noch keinen reproduzierbaren
SQLCipher-Packagingpfad mit eigener Spec und Manifestkette. Für das getrennte
Produktziel existiert nun eine nicht aktivierte macOS-arm64-
Buildbasis: Sie bindet SQLCipher 4.17.0 und `sqlcipher3` 0.6.2 an exakte
Quellhashes, erzeugt eine lokal als `0.6.2+jkm.sqlcipher4170.1` markierte
CommonCrypto-Extension für Python 3.14.6 zweimal bytegleich und prüft das Wheel
in einem dritten temporären Venv. Das Wheel ist kein Repositoryartefakt und
wird von Pilot-, App-, DMG-, Startup- oder Produktpfaden nicht konsumiert.

Für ein späteres Produkt bleibt SQLCipher 4.17.0 aus einem kontrollierten,
hash-gepinnten macOS-/Windows-Build das Ziel. Produktive Schlüsselhierarchie,
Migration, Startup, Backup/Restore, Signierung, Notarisierung, Windows und
Release sind ausdrücklich offen. RC `0.2.2`, Pilotdaten, `security.sqlite`,
fachliche SQLite, Dokumente, Backups, Appcast und UI bleiben unverändert.

## Security Sprint 2 - Key Foundation und DMK-Lifecycle

Als isolierter Entwicklungsstand besteht eine Qt-freie Grundlage für einen
zufälligen 256-Bit-Data-Master-Key (DMK), versionierte Keysets mit den Zuständen
`pending`, `active`, `revoked` und `failed`, ein kanonisches Key-Envelope-Format
sowie einen getrennten macOS-Keychain-Adapter. Der gemeinsame Plattformport ist
für eine spätere Windows-DPAPI-/Credential-Manager-Implementierung vorbereitet.

App-Passwort, Gerätecredential, Supportschlüssel und DMK bleiben getrennte
Konzepte. Ein Passwortwechsel verändert den DMK nicht. Der aktuelle Stand wird
nicht vom App-Start aufgerufen, verschlüsselt keine fachliche Datenbank, keine
Dokumente und keine Backups und verändert weder UI noch Pilotdaten.

Release Candidate `0.2.2`, `security.sqlite` und seine Schema-Version 3 bleiben
unverändert. Die Entwicklung verwendet ausschließlich einen neuen, nicht in
RuntimePaths registrierten Metadaten-Sidecar für technische Keyset-Daten. Es
gibt keine Migration, keine Startup- oder Releaseintegration und keine
Produktivfreigabe. Der Sidecar ist noch nicht kryptografisch authentifiziert;
bei uneindeutiger Längen-/Fingerprint-Korruption blockiert der Lifecycle, ohne
den möglicherweise korrekten Plattform-DMK automatisch zu löschen.

## Sprint 0.2S.1 - Support-Assistent UX

Der Betreiber erhält mit `Jenaplan Support-Assistent.app` eine vom
Kompetenzmanager, Pilotpaket und Updatepfad getrennte grafische macOS-arm64-
Anwendung. Sie macht den bereits geprüften Offline-Support-Reset verständlich,
ohne Protokoll, Kryptografie, Tokenformat, Schlüsselmodell, Backupvertrag,
Appfunktion oder Schülerdatenmodell zu verändern.

Der Assistent verarbeitet nur eine bewusst gewählte technische Anfrage, einen
bewusst gewählten externen verschlüsselten Privatschlüssel und flüchtigen
UI-State. Fachliche SQLite, Security Store, Dokumente, Backups und Runtime-
Daten liegen außerhalb seiner Architektur- und Paketgrenze.

## Sicherer macOS-Updatepfad ab Sprint 0.2U.1

Sprint 0.2U.1 entscheidet die Architektur, implementiert aber noch keinen
produktiven Updater. Der unveränderte Release-Kandidat `0.2.0` besitzt keinen
Updateclient und wurde Laura nicht installiert. Ihre erste Installation ist
deshalb direkt ein bewusst manuell geöffnetes Pilot-DMG `0.2.1`; erst diese
Version enthält den für den beaufsichtigten Pilotkanal konfigurierten
Sparkle-2-Client. `0.2.2` / Build `202` ist das erste beaufsichtigte
Sparkle-Folgeupdate. Ein gleichnamiger Neuaufbau von `0.2.0` wird wegen nicht
unterscheidbarer Installationen verworfen.

Der spätere Updatepfad ersetzt ausschließlich das unveränderliche App-Bundle.
Fachliche SQLite, verwaltete Dokumente, Exporte, Backups, Logs, Security Store,
AppPreferences und nicht synchronisierender macOS-Schlüsselbund bleiben
außerhalb des Bundles. `0.2.2` enthält deshalb weder Fach- noch
Securitymigration. Der ad-hoc-signierte Einzelpilot behauptet weder Developer ID noch
Notarisierung. Produktive Veröffentlichung bleibt gesperrt, bis Developer ID,
Hardened Runtime, Notarisierung/Stapling, signierter HTTPS-Appcast, externer
privater EdDSA-Schlüssel und der reale Schlüsselbund-/Touch-ID-Übergang von der
ad-hoc-signierten Pilotbasis nachgewiesen sind. Details regelt ADR-073.

## Historischer Ursprung des produktiven Supportbetriebs (Sprint 0.2B.6)

Der vorhandene App- und Security-Vertrag bleibt unverändert. Neu ist ein
vollständig getrenntes macOS-arm64-Supportpaket mit Finder-Startern für
Token-Signatur und bewusste externe Schlüsselbereitstellung. Es arbeitet
offline, liest keine fachliche Runtime und wird weder App-/DMG- noch Laura-
Paketbestandteil. Der private Schlüssel wird ausschließlich außerhalb des
Repositorys verschlüsselt als PKCS#8 mit restriktiven Rechten erzeugt.

Die produktive Public-Key-Registry besitzt einen strikt versionierten,
deterministisch validierten Einbindungsweg für mehrere aktive, rotierende,
retirierte und widerrufene öffentliche Schlüssel. Die erstmalige Aktivierung
von `support-2026-b` geschah historisch mit 0.2.2; der dokumentierte
0.3.0-Stand führt diesen lokalen Support-Reset weiter. Privater Schlüssel und
Passphrase bleiben extern. Rotation und Widerruf erfordern weiterhin einen
neuen geprüften App-Release.

## Historischer Pilot-Release-Kandidat 0.2.0

Version `0.2.0` fasst den implementierten lokalen Security-, Betriebs- und
Onboardingstand als technisch prüfbaren Pilot-Release-Kandidaten zusammen. Die
kanonische Version stammt aus `src/version.py`; App-Metadaten, Build-Info, DMG
und Dokumentbuild übernehmen sie ohne zweite Versionsquelle.

Der Release-Kandidat startet ohne Schüler-, Pilot- oder Runtime-Daten. Die
App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
FileVault und ein geschütztes macOS-Benutzerkonto bleiben erforderlich. Der
produktive Support-Reset ist ab `0.2.2` für den beaufsichtigten Pilotbetrieb als
betreuter Ausnahmeweg freigeschaltet. Recovery-Code bleibt der erste Weg.

Technisch nicht durch reale Hardwareabnahme ersetzt sind echter Sleep/Wake, die
physische Touch-ID-Systemaufforderung mit Fingerabdruck, App-Switcher und die
vollständige Aktivierungs-/Widerrufsreise. Developer-ID-Signierung,
Apple-Notarisierung sowie die reale Keychain-/Touch-ID-Prüfung nach dem Update
auf Lauras Mac bleiben ebenfalls offen.

## Historischer Support-Reset-Ablauf ab Version 0.2B.5

Wenn Passwort und Recovery-Codes nicht mehr verfügbar sind, kann die App eine
rein technische Reset-Anfrage erzeugen. Sie wird nicht automatisch übertragen
und enthält keine Schüler-, Dokument-, Schul-, E-Mail- oder Betriebssystemdaten.
Support prüft die Identität organisatorisch außerhalb der App und signiert die
Anfrage mit einem extern verwahrten privaten Ed25519-Schlüssel.

Die App prüft Tokenformat, Signatur, öffentlichen Schlüssel, Installation,
Nutzer, Anfrage, Nonce, Aktion und Zeitfenster. Der Reset erfolgt erst nach einer
zweiten bewussten Bestätigung und einem erfolgreich erzeugten und erneut
verifizierten fachlichen Sicherheitsbackup. Danach sind altes Passwort,
Recovery-Codes, gespeicherte Geräteanmeldung, Touch ID und laufende Sitzung
unwirksam; die App endet in `password_reset_pending` und beendet sich.

Beim nächsten Start werden neues Passwort, neuer Recovery-Satz und bewusste
Sicherungsbestätigung verlangt. Fachliche Daten, IDs, Dokumentpfade,
Backupformat, Anzeigename und Onboardingstatus bleiben unverändert. Der Prozess
entschlüsselt nichts und ist kein Masterkennwort.

Ab Version `0.2.2` enthält die Default-Key-Registry genau den vom Product Owner
bestätigten öffentlichen Schlüssel `support-2026-b`. Die UI kann damit
signierte Codes produktiv prüfen. Private Schlüssel, Passphrase und zentrale
Audit-/Cloudsysteme sind nicht Bestandteil der App.

## Geräteanmeldung und Touch ID ab Version 0.2B.4a

`Auf diesem Gerät angemeldet bleiben` bezeichnet eine widerrufbare lokale
Geräteanmeldung, keine dauerhafte App-Sitzung. Nach ausdrücklich bestätigter,
erfolgreicher Passwortanmeldung speichert macOS ausschließlich ein zufälliges
256-Bit-Gerätegeheimnis im nicht synchronisierenden Schlüsselbund. Das Passwort
wird niemals gespeichert; Security Store v3 enthält nur Salt, versionierten
Hash und technische Bindungs-/Statusmetadaten. Eine neue Sitzung entsteht erst
am Auth-Gate und endet beim Schließen der App.

Manuelle, Inaktivitäts- und Wake-Sperre bleiben aktiv. Nach einer Sperre kann
auf unterstützten Macs optional echtes Touch ID verwendet werden; das Passwort
bleibt jederzeit sichtbar verfügbar. Abbruch, fehlende Einrichtung, Lockout,
Systemabbruch oder Credential-Inkonsistenz öffnen die App nicht, sondern führen
zum Passwortpfad. Passwortänderung, Recovery und Support-Reset widerrufen über
die Security-Epoch alle gespeicherten Geräteanmeldungen.

Die Funktion verschlüsselt keine fachliche SQLite-Datenbank, Dokumente oder
Backups. `.jkmbackup`, Restore, Diagnose und AppPreferences enthalten kein
Gerätegeheimnis und keine Credential-Metadaten. Nicht-macOS-Plattformen bleiben
ohne Dummy-Sicherheit vollständig passwortfähig. Die reale physische Abnahme
von Sprint 0.2B.4, insbesondere echter Sleep/Wake, bleibt offen.

## Security Core ab Version 0.2

Sprint 0.2B.4 integriert den Core produktiv. Restore-Recovery bleibt vor der
Authentifizierung; die fachliche Runtime samt Pilotdaten, Produktordnern,
SQLite-Adaptern und `AppShell` entsteht erst nach erfolgreichem Erstkonto,
Login oder abgeschlossenem Passwort-Reset. Neuinstallationen und vorhandene
ungeschuetzte Installationen erhalten genau ein lokales Konto mit zehn einmalig
angezeigten Recovery-Codes.

Die Sitzung existiert nur im Arbeitsspeicher und wird durch `user_id`,
`installation_id` und `security_epoch` gebunden. Manuelle Sperre, Inaktivitaet
und Wake zeigen eine opake neutrale Sperransicht und erhalten ungespeicherte
In-Memory-Eingaben. Die Sicherheitseinstellungen bieten feste Intervalle,
Passwortwechsel, Recovery-Code-Erneuerung und `Jetzt sperren`.

Ein optionaler lokaler Anzeigename gehoert zum allgemeinen App-Profil, nicht
zum Authentifizierungskonto. Er wird bei Erstkonto/Legacy-Aufnahme freiwillig
erfasst, spaeter im getrennten Bereich `Persönliche Begrüßung` geaendert und
fuer eine dezente tageszeitabhaengige Dashboard-Begruessung verwendet. Der
atomare Store `<runtime-root>/app-preferences.json` bleibt ausserhalb von
Security-SQLite, fachlicher SQLite, Support-Reset und `.jkmbackup`.

Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
FileVault und ein geschuetztes Betriebssystemkonto bleiben empfohlen. Die
gespeicherte Geräteanmeldung, macOS-Keychain, Touch ID und die
Support-Reset-Token-UI sind im Stand 0.2 umgesetzt. Windows Hello und eine
Verschluesselung der fachlichen Dateien sind nicht Bestandteil dieses Stands.

Die reale Pilot-Mac-Abnahme der 0.2B.4-Sicherheitsintegration bleibt trotz
automatisierter und Offscreen-Pruefungen weiterhin offen, solange die
physische Bedienungshilfen-basierte Abnahme nicht nachgeholt wurde.
Insbesondere ist echter Sleep/Wake auf dem Pilot-Mac noch nicht physisch
bestaetigt.

## Erste Schritte ab Version 0.2C.1

Nach erfolgreicher Authentifizierung und Aufbau der fachlichen Shell kann die
Lehrkraft einmalig eine kurze Orientierung `Erste Schritte` erhalten. Der Flow
ist kein fachlicher Assistent: Er erklaert Zweck und Reihenfolge, zeigt nur
vorhandene Bereiche und navigiert zu bestehenden Seiten. Er erzeugt keine
Stammgruppen, Kurse, Kinder, Beobachtungen, Backups, Beispiel- oder
Pilotdaten.

Der Status liegt rein lokal in
`<runtime-root>/app-preferences.json` und ist weder Security-Attribut noch
fachlicher Datenbestand. Fachliches Restore, Support-Reset, Passwortwechsel und
Recovery veraendern ihn nicht. Bestehende Installationen ohne Onboarding-Status
duerfen beim ersten Start dieser Produktversion einmal die Orientierung sehen;
`completed` und `dismissed` oeffnen nicht erneut automatisch. Unter
`Einstellungen` kann `Erste Schritte erneut öffnen` bewusst aufgerufen werden.

Der kindbezogene Fachschritt verweist auf den bestehenden Qt-Weg `Schüler` ->
`Profil öffnen` -> `Überblick` -> `Fächer für die Dokumentation` ->
`Aufklappen` -> `Für dieses Kind individuell festlegen`. Er erklärt die zehn
Unterrichtsfächer als priorisierten Dokumentationskontext, nicht als Löschung
oder Berechtigungsgrenze. Die beiden überfachlichen Entwicklungsbereiche
bleiben immer verfügbar; weitere aktive Unterrichtsfächer bleiben im
Beobachtungsdialog unter `Weitere Fächer` erreichbar.

Die Architektur besitzt einen fachlich getrennten Security Core unter
`<runtime-root>/security/`. Historisch war die App-Sperre zunächst nur die
Authentisierungsschicht; der heutige Final-V4-Produktpfad verschlüsselt
Datenbank, verwaltete Dokumente und Backups zusätzlich. Der Security Store
wird nicht als fachlicher Bestand gesichert, restored, exportiert oder
diagnostiziert und ist nicht mit fachlichen IDs oder Inhalten verbunden.

Historisch lieferten Sprint 0.2B.2 zunächst nur den testbaren Core und Sprint
0.2B.3 den offline signierten Ed25519-Support-Reset. Die damals noch offenen
Start-, Sitzungs-, Login-, Recovery- und Reset-Oberflaechen wurden durch Sprint
0.2B.4 und 0.2B.5 umgesetzt. Version `0.2.2` schließt die betriebliche
Freischaltung mit einem freigegebenen öffentlichen Produktivschlüssel ab.

## Historischer Produktstand vor Final V4

Der Jenaplan-Kompetenzmanager ist eine lokale Python-/PySide6-Desktop-Anwendung fuer Lehrkraefte. PySide ist die aktive Produktoberflaeche, SQLite die produktive lokale Datenhaltung.

Der implementierte Stand nach Sprint 10B und den anschliessenden Schuelerprofil-UX-Korrekturen umfasst die zentralen Arbeitsbereiche fuer Stammdaten, Unterrichtsalltag, Beobachtung, Kompetenzdokumentation, Schuelerprofil, Lernentwicklungsbericht und Lernentwicklungsgespraech. Unveraenderliche Bericht- und LEG-Revisionen sowie daraus erzeugte PDF-Artefakte sind produktiv umgesetzt.

Das Projekt befindet sich in der **Produktreifephase**. Der dokumentierte
Stand ist Version `0.3.0` / Build `303` mit lokaler Anmeldung, Keychain,
optionalem Touch ID, Sperre, Support-Reset, ZIP-v1-Backup/Restore,
Restore-Worker, Bericht-/LEG-Entwurfsauswahl, Revisionen und PDF-Ausgaben.
Der Schwerpunkt liegt auf Konsistenz, Barrierearmut, Pilotierbarkeit,
Dokumentationsqualität, Betriebsentscheidungen und Release-Vorbereitung. Ein
Buildartefakt, eine reale Pilotabnahme oder App-Store-Entscheidung folgt daraus
nicht.

Excel/VBA ist eine historische Vorstufe. Die damalige Workbook-Linie wird unter `legacy/excel/` als Referenz erhalten, ist aber weder Zielplattform noch aktiver Produktpfad. Historische Workbook-Versionen wie `v0.4` und fruehere Ausgabedateien sind keine aktuellen Hauptartefakte.

## Planung nach der veröffentlichten Build-400-Basis

Die unmittelbar nächste Phase ist die reale fachliche, ergonomische und
betriebliche Prüfung des veröffentlichten Pilotstands sowie die Behebung
ausschließlich tatsächlich beobachteter pilotkritischer Fehler. Pilottestpunkte
sind Validierungen und noch keine automatisch beschlossenen
Funktionsänderungen.

Der Schuljahreswechsel ist in Build 400 vollständig umgesetzt und gehört nicht
mehr zur Zukunftsplanung. Der kleinste empfohlene nächste fachliche
Planungsschritt ist ein Discovery-/Architecture-Gate für den
Schülerlisten-Import; ein Implementierungssprint folgt daraus nicht
automatisch. Mehrkind-Schnellbeobachtung beziehungsweise Gruppenbeobachtung und
Klassen-/Kursmatrix bleiben von realen Pilotbefunden abhängig. Keiner dieser
Kandidaten ist derzeit als Implementierungssprint freigegeben. Vor einer
Freigabe folgen Product Discovery, Produktentscheidung, Datenmodell-,
Architektur-, Datenschutz- und UX-Review.

## Projektziel

Der Kompetenzmanager unterstuetzt Lehrkraefte an Jenaplan-Grundschulen bei der strukturierten, nachvollziehbaren und alltagstauglichen Dokumentation von Lernentwicklung nach dem Thueringer Lehrplan.

Das Produkt soll den Dokumentationsaufwand reduzieren, ohne paedagogische Entscheidungen zu automatisieren. Beobachtungen, bestaetigte Kompetenzstaende, Berichte und Lernentwicklungsgespraeche bleiben fachlich unterscheidbare Arbeits- und Ausgabekontexte.

## Paedagogische Leitlinien

- Beobachtung steht vor Bewertung.
- Dokumentierte Ereignisse bleiben bis zum konkreten Beleg nachvollziehbar.
- Entwicklung wird aus realen Beobachtungen und Bestaetigungen sichtbar, nicht aus erfundenen Zwischenwerten.
- Fehlende Dokumentation ist kein negativer Leistungsstatus.
- Automatische Projektionen liefern Orientierung, aber keine fertigen paedagogischen Aussagen.
- Lehrkraefte verantworten manuelle Berichtstexte, Gespraechsinhalte und bewusste Evidenzauswahl.
- Status, Dokumentationsabdeckung und Entwicklung duerfen nicht allein durch Farbe vermittelt werden.

## Abgeschlossene Kernfunktionen

### Ergänzungen der veröffentlichten Build-400-Basis

- vollständiger Schuljahreswechsel mit Vorschau, Planauflösung,
  Passwort-Step-up, Pflichtbackup, Maintenance, atomarer Aktivierung,
  Rollback und Historie
- gemeinsamer sicherer read-only In-App-PDF-Viewer für finale verschlüsselte
  RPA-/LCA-Artefakte
- direkte Schülerprofilnavigation aus `Passende Kinder für diese Stunde` mit
  davon getrennter Aktion `Beobachten`
- Beobachtungskontext `Partnerarbeit`
- sichtbare Stammgruppe in kombinierten Kurs-, Kursverbund- und
  Gesamtschülerlisten
- Fachillustrationen beziehungsweise Fachvignetten als dekorative,
  ID-gebundene Orientierung ohne neue Fachlogik

### Stammdaten und Unterrichtskontext

- persistente Schueler-, Stammgruppen-, Kurs- und Kursverbundverwaltung
- stabile technische IDs und kontrollierte Archivierungs- beziehungsweise Aktivitaetsregeln
- persistenter Wochenstundenplan mit Stammgruppen-, Kurs- und Kursverbundkontext
- read-only Dashboard `Heute` mit aktueller beziehungsweise naechster Stunde, Tagesverlauf, Dokumentationsorientierung und direkten Arbeitswegen

### Beobachtungen und Dokumente

- Beobachtungen mit Datum, Kontext, Notiz, Kompetenzzuordnung und Einzelbewertungen
- Schnellbeobachtungen ohne erzwungene Kompetenzzuordnung
- Bearbeiten und Soft Delete ueber den bestehenden Application-/Repository-Pfad
- studentenzentrierte Dokument- und Medienreferenzen ohne Datei-BLOBs in SQLite
- historisch sichere Darstellung nicht mehr aktiver oder nicht mehr verfuegbarer Referenzen

### Schuelerprofil und Kompetenzen

- kindbezogener Arbeitsraum mit dauerhaft sichtbarem Schuelerkontext
- Profilueberblick nach der produktiven Variante-A-UX
- dokumentationsbezogene Orientierungskarten, Kompetenzuebersicht, neueste Beobachtungen und neutrale Hinweise auf noch nicht dokumentierte Bereiche
- Kompetenz-Cockpit mit der Hierarchie `Fach -> Kompetenzbereich -> Thema -> Kompetenz`
- kanonische Trennung von bestaetigtem Stand, berechnetem Vorschlag und Beobachtungsevidenz
- Maus-, Tastatur-, Fokus- und Accessibility-Vertraege fuer zentrale Profilinteraktionen

### Lernentwicklungsbericht

- persistenter bearbeitbarer Berichtsentwurf `RPD`
- bewusst ausgewaehlte Fach-, Kompetenz-, Beobachtungs- und Diagrammreferenzen
- manuell verantwortete Gesamt- und Fachtexte
- stabiles Berichtaggregat `RPT` mit unveraenderlichen Revisionen `RPV`
- snapshotbasierte historische Leseansicht mit Integritaetspruefung
- unveraenderliches finales PDF-Artefakt `RPA` genau einer aktuellen finalisierten Revision

### Lernentwicklungsgespraech

- persistenter, live-referenzierender LEG-Arbeitsentwurf `LCD`
- phasenorientierter Arbeitsraum fuer Vorbereitung, Gespraech und gemeinsam festgehaltene Ergebnisse
- bewusst ausgewaehlte Kompetenz- und Beobachtungsbelege
- stabiles LEG-Aggregat `LCF` mit unveraenderlichen Revisionen `LCV`
- snapshotbasierte historische Leseansicht mit Integritaetspruefung
- unveraenderliches finales PDF-Artefakt `LCA` genau einer aktuellen abgeschlossenen Revision

## Aktive Systemarchitektur

Die aktive Schichtenfolge lautet:

```text
PySide UI
-> ViewModels
-> Desktop Adapter
-> Application Commands und Queries
-> Domain Services und Validatoren
-> Repositories
-> SQLite
```

Fuer Ausgaben gilt zusaetzlich:

```text
verifizierter fachlicher Snapshot
-> renderer-neutrales Ausgabemodell
-> reiner PDF Renderer
-> unveraenderliche Datei und Artefaktreferenz
```

Fuer den lokalen macOS-Pilotbetrieb gilt:

```text
spaeter separat geprueftes App-Bundle
-> unveraenderliche eingebettete Laufzeit und Ressourcen
-> getrennter Benutzerpfad unter ~/Library/Application Support/
-> keyed Final-V4-SQLCipher und keyed Dokument-Companion
-> verschluesselte Managed Documents und .jkmebackup ausserhalb der App
```

Der veröffentlichte Apple-Silicon-Pilotbuild 0.4.0 / Build 400 wurde
reproduzierbar mit PyInstaller aus `e96a77e` erzeugt und setzt macOS 13 voraus.
Die Übergabevariante enthält keine Schülerdaten. Der abweichende aktuelle
Quellstand `926582f` darf nicht erneut als Build 400 paketiert werden; ein
Folgebuild benötigt mindestens Build 401 und eine noch offene PO-Entscheidung
zur sichtbaren Version. Developer ID, Notarisierung, Stable-Freigabe,
Appcast-Aktivierung und schulische Betriebsfreigabe bleiben getrennte Gates
und werden durch die Pilotveröffentlichung nicht behauptet.

### Architekturprinzipien

- Widgets enthalten keine Businesslogik und greifen nicht direkt auf SQLite zu.
- SQLite und die dokumentierten Datenquellen bilden die fachliche Source of Truth.
- Repositories kapseln Persistenz; Application- und Domain-Schichten verantworten Schreibprozesse und Validierung.
- ViewModels und Adapter liefern displayfertige Projektionen, ohne fachliche Daten in der UI neu zu berechnen.
- Jede Funktion besitzt eine Implementierung, kann aber mehrere Einstiegspunkte haben.
- Schuelerprofil, Bericht und LEG verwenden dieselbe kanonische Kompetenz- und Evidenzprojektion, ohne eigene Statuslogik zu entwickeln.
- Historische Snapshots werden vor jeder Lese- oder PDF-Projektion gegen ihren gespeicherten SHA-256 geprueft.
- `PdfRenderer` kennt weder SQLite noch Repositories, Draftstatus oder fachliche Freigaberegeln.
- Bericht und LEG bleiben getrennte fachliche Domains mit getrennten Aggregaten, Revisionen und Artefakten.
- Schema- und Datenmodellveraenderungen erfolgen nur nach Product-Owner-, Datenmodell- und Architekturreview.

## Datenhaltung und Dateien

- Produktive lokale Datenbank: keyed Final V4 auf SQLCipher 4.17 im
  verwalteten Final-V4-Runtimebereich
- Produktiver Dokument-Companion: keyed SQLCipher-Companion derselben
  Database-Key-Runtime
- Lehrplanbasierter Kompetenzkatalog: `data/curriculum_catalog_v1.csv`
- Konfiguration und Farbreferenzen: strukturierte Dateien unter `data/`
- Verwaltete Schuelerdokumente: verschlüsselte Generationen im zentralen
  `ManagedDocumentStore`
- Finale Bericht- und LEG-Artefakte: verschlüsselte verwaltete Generationen;
  fachliche Artifact-ID und physische Storage-Generation bleiben getrennt
- Backups: ausschließlich installationsgebundene `.jkmebackup` im
  Cipher-Produktpfad

Der keyed Companion speichert fuer Dokumente und PDF-Ausgaben Metadaten,
Generationen und aktive Referenzen. Dokumentcontainer bleiben getrennte
verschlüsselte Dateien. Produktive Beziehungen verwenden stabile IDs und nicht
sichtbare Namen oder UI-Positionen. Standard-SQLite, Klartextdokumentablage und
ZIP-v1 sind keine produktiven Fallbacks.

## Produkt- und Ausgabemodell

### Schuelerprofil

Das Schuelerprofil ist eine aktuelle Live-Arbeitsansicht. Es zeigt dokumentierte Staende, Evidenz, Dokumentationsabdeckung und Arbeitswege, ist aber kein offizielles oder eingefrorenes Dokument.

### Bericht

Der Berichtsentwurf bleibt bearbeitbar und live-referenzierend. Eine bewusste Finalisierung erzeugt beziehungsweise aktualisiert ein stabiles Berichtaggregat und schreibt eine neue unveraenderliche Revision. Korrekturen erfolgen als Folgerevision; fruehere Revisionen bleiben historisch lesbar.

### Lernentwicklungsgespraech

Der LEG-Entwurf bleibt ein eigener bearbeitbarer Gespraechsarbeitsstand. Ein expliziter Abschluss friert ausschliesslich den reproduzierbaren Gespraechskontext, gemeinsame Ergebnisse und bewusst ausgewaehlte Belege in einer unveraenderlichen LEG-Revision ein. Interne Vorbereitung wird nicht automatisch Teil des Abschlusses.

### PDF-Artefakte

PDF ist ein Ausgabeformat und keine Fachschicht. Finale Bericht- und LEG-PDFs werden ausschliesslich aus der jeweils aktuellen, hashverifizierten Revision erzeugt. Drafts, Widgets und spaetere operative Daten sind keine Quellen eines finalen PDF-Artefakts. Ein vorhandenes Artefakt wird bei erneutem Aufruf verifiziert und nicht ueberschrieben.

## Informationsarchitektur und Design-System

Die globale Navigation trennt `ARBEIT` mit `Heute` und `Schueler` von `VERWALTUNG` mit `Stammdaten` und `Einstellungen`. Beobachtungen, Kompetenzen, Berichte und LEG bleiben ueber den Kindkontext erreichbar.

Das verbindliche PySide-Design-System ist in `docs/DESIGN_SYSTEM.md` dokumentiert. Es definiert Tokens, Typografie, Flaechen, Karten, Tabellen, Dialoge, Fokus, Reduced Motion, Tastaturbedienung und Accessibility. Historische Workbook-Layouts, feste Zellpositionen und Excel-Zoomstufen sind keine Designreferenz der aktiven Produktlinie.

Zentrale UX-Prinzipien:

- ruhige, lehrkraftzentrierte Informationshierarchie
- genau eine dominante Aktion pro Arbeitskontext
- ganze sinnvolle Zeilen und Karten als ausreichend grosse Interaktionsflaechen
- progressive Disclosure fuer Evidenz und historische Details
- sichtbare Fokuszustaende und vollstaendige Tastaturwege
- Status nie ausschliesslich ueber Farbe
- responsive Desktop-Zielgroessen 1180 x 760, 1280 x 800 und 1400 x 900

## Prototypen und Product Discovery

In `prototypes/` abgelegte UX-Studien sind isolierte Entscheidungs- und Referenzartefakte. Sie verwenden fiktive Daten und werden erst nach ausdruecklicher Produktentscheidung in die produktive App uebertragen. Ein Prototyp ist weder Datenquelle noch produktive Nebenanwendung.

## Historische Excel-/VBA-Linie

Die fruehere Excel-/Workbook-Architektur, VBA-Interaktionsschicht, UserForm- und Worksheet-Dialogspikes sowie die historische Version `v0.4` bleiben als Projektgeschichte dokumentiert. Ausfuehrbare Altstaende und Quellen liegen unter `legacy/excel/`.

Fuer die aktive Produktlinie gilt:

- keine neuen Excel- oder VBA-Funktionen
- keine Workbook-Datei als aktuelles Hauptartefakt
- keine VBA-/AppleScript-Smoke-Tests als Standardpruefung
- Excel/openpyxl nur bei ausdruecklichem Legacy- oder Exportauftrag

Historische Sprint- und ADR-Texte bleiben als damaliger Entscheidungsstand lesbar, werden aber als historisch oder durch die PySide-/SQLite-Linie abgeloest gekennzeichnet.

## Dokumentationssystem

- `PROJECT.md`: aktueller Produktstand und dauerhafte Projektgrundlagen
- `SPRINTS.md`: operative Planung und historisch gekennzeichnete Sprintstaende
- `DECISIONS.md`: Architekturentscheidungen und ihr Umsetzungsstatus
- `CHANGELOG.md`: chronologische Aenderungen ohne Vorwegnahme einer Release-Version
- `docs/PROJECT_CONSTITUTION.md`: verbindliche Projektverfassung
- `docs/TECHNICAL_NAMES.md`: technische Namen und IDs
- `docs/DATA_REGISTRY.md`: Datenquellen und Persistenzobjekte
- `docs/DATA_LIFECYCLE.md`: Schreib-, Historien- und Loeschprozesse
- `docs/VIEW_DATA_OWNERSHIP.md`: Owner und Quellen der Ansichten
- `docs/UI_DATA_MAPPING.md`: sichtbare UI-Felder und ihre Datenquellen
- `docs/DESIGN_SYSTEM.md`: verbindliches PySide-Design-System

Neue Architektur-Dokumente werden nur eingefuehrt, wenn eine echte Luecke nicht in den bestehenden Governance-Dokumenten geschlossen werden kann.

## Rollen und Entwicklungsreihenfolge

- Product Owner: gibt neue Funktionen, fachliche Aenderungen und Datenmodellaenderungen frei.
- Fachliche Review: prueft paedagogische Verstaendlichkeit, Lehrplanbezug und nicht bewertende Darstellung.
- UX-/Accessibility-Review: prueft Informationshierarchie, Bedienbarkeit, Tastatur, Fokus und Kontrast.
- Technische Review: prueft Architekturgrenzen, Wartbarkeit, Integritaet und Lauffaehigkeit.

Jede Implementierung folgt dieser Reihenfolge:

1. Vision
2. Product Discovery
3. Produktentscheidung
4. Datenmodell-Review
5. Architektur-Review
6. UX-Review
7. Prompt-Review
8. Implementierung
9. Technical Review
10. Test
11. Commit

## Aktueller Entwicklungsstatus

Die veröffentlichte Produktbasis ist 0.4.0 / Build 400 aus `e96a77e`.
`926582f` ergänzt die unveröffentlichte Korrektur der individuellen
Dashboard-Fachrelevanz. Die Weiterarbeit vom 07.09.2026 ergänzt die oben
genannten fünf freigegebenen Funktionen. Vor einer neuen Paketierung bleibt
eine monotone Buildanhebung erforderlich.

Aktuelle Arbeitsschwerpunkte sind:

- reale fachliche, ergonomische und betriebliche Pilotpruefung
- befundbasierte Fehlerbehebung und die fünf freigegebenen Komfortfunktionen
- Accessibility- und Tastaturqualitaet
- robuste Desktop-Darstellung in den festgelegten Zielgroessen
- fachlich-technische Vorbereitung des Schülerlisten-Imports
- Betriebs- und Datenschutzentscheidungen ohne Vorwegnahme einer Auslieferung

Weiterhin offen und durch diesen Dokumentationsabgleich nicht freigegeben sind
insbesondere:

- `Zuletzt bearbeitet` auf `Heute`;
- bewusster Klartextexport finaler verschlüsselter RPA-/LCA-Artefakte;
- Implementierung des Schülerlisten-Imports nach abgeschlossener Vorbereitung;
- Mehrkind-Schnellbeobachtung beziehungsweise Gruppenbeobachtung;
- Klassen-/Kursmatrix.

Darüber hinaus bleiben Product-Owner- beziehungsweise Betriebsentscheidungen
zu Rollen und Berechtigungen, Aufbewahrung und Zugriffsschutz, weitergehender
Archivierung, Renderer-Versionierung, mehreren Artefakten pro Revision sowie
einem möglichen gemeinsamen, klar getrennten Bericht-/LEG-Ausgabepaket offen.

## Definition of Done

Eine Aenderung gilt als abgeschlossen, wenn:

- die freigegebene fachliche Anforderung umgesetzt oder dokumentiert ist,
- keine Projekt- oder Architekturregel verletzt wurde,
- Datenquellen, technische Namen, Lifecycle und UI-Mapping konsistent dokumentiert sind,
- das Changelog aktualisiert wurde,
- fokussierte und risikogerechte Pruefungen erfolgreich sind,
- die PySide-Anwendung weiterhin importierbar und offscreen startbar ist,
- keine nicht freigegebene Funktion oder Datenmodellentscheidung eingefuehrt wurde.
