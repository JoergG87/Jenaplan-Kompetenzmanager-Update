# iPad-Machbarkeitstest

## Gesamte isolierte App: aktueller Simulatorstand 12.10.2026

Die ursprüngliche Dreiauswahlprobe unten bleibt historische Referenz. Die vollständige Test-App verwendet `src/tablet_app/`, die ursprüngliche AppShell und dieselben kanonischen Python-/SQLite-Verträge. Bundle-ID: `de.jenaplan.kompetenzmanager.ipad-app-test`. Daten ausschließlich in der eigenen App-Sandbox unter der festen Rolle `synthetic-tablet-app`; kein produktiver Mac-Pfad oder Schlüsselbund. Fehlende/ungültige Testautorität bricht ab, bestehende Daten werden beim Update erhalten. Final-V4 bleibt unverändert.

`scripts/build_ipad_app.py` stellt einen leeren, ungeschützten Zielordner bereit und erzeugt die eigene Konfiguration. Parameter: `--stage`, `--deploy-tool`, `--pyside-wheel`, `--shiboken-wheel`, `--python-xcframework`, wiederholtes `--dependency-wheel`. Offizielle passende ARM64-Simulator-Wheels und Python.xcframework erforderlich; Pillow, ReportLab und charset-normalizer separat. Erzeugtes Xcode-Projekt mit `ARCHS=arm64 ONLY_ACTIVE_ARCH=YES CODE_SIGN_IDENTITY=-` bauen. Nach jedem inkrementellen Quellbuild das fertige Simulator-App-Bundle ausdrücklich mit `codesign --force --sign - <App-Pfad>` erneut ad-hoc signieren und mit `codesign --verify --deep --strict <App-Pfad>` prüfen. Xcode erkennt zusätzlich kopierte Python-Ressourcen nicht zuverlässig als Signaturänderung; BUILD SUCCEEDED allein genügt nicht. Keinen Geräterelease aus dem Simulatorpaket ableiten.

Lokaler Build: `output/ipad-app/build/DerivedData/Build/Products/Debug-iphonesimulator/Jenaplan-iPad-App-Test.app`. Aktuelle Prüfergebnisse in PROJECT.md und CHANGELOG.md; Bilder unter `output/ipad-app/screenshots/refined/`, vollständiger Pflanzenexport unter `output/ipad-app/Kompetenzexport-Simulator-Mila.pdf`. Alle dargestellten Kinder und Eingaben sind synthetisch. Gerätesignierung, echte Hardware, Files-Import/Backup/Restore und Schutz-/Accessibility-Abnahme bleiben offen. Kein Produktrelease.

## Historie: erste Dreiauswahlprobe

Separater Prototyp, kein Produktbuild. Drei feste synthetische Kompetenzen,
explizite Auswahl, Standard-SQLite und Wiederöffnung. Keine realen Schülerdaten,
keine Produktmodule, kein Zugriff auf Mac-Produktdaten oder Schlüssel.
Die Testtabelle verändert das Produktdatenmodell nicht.

## Aktueller Nachweis

ARM64-Simulatorbuild mit Qt/PySide 6.12.0 und Python 3.15.0rc2 unter
Xcode 27.0 erfolgreich, tiefe strikte Ad-hoc-Signaturprüfung bestanden.
Nach Mac-Neustart im eigenen iPadOS-27.0-Simulator installiert und gestartet.
Drei Auswahlen über die Oberfläche gespeichert: `--`, `+`, `++`.
Die SQLite-Datei im eigenen App-Container enthält genau diese drei Zeilen.
Nach vollständigem Beenden und Neustart werden alle drei Auswahlen wieder
angezeigt. Hoch- und Querformat visuell lesbar; Auswahl und Speichern bedienbar.

Drei Repository-Tests bestanden auf macOS: Speicherung und Wiederöffnung,
ungültige Auswahl ohne Änderung, Abweisung fremder Datenbanken und Symlinks.
Ein Offscreen-Test prüft Auswahl und Speicherung über das Fenster.
Keine Prüfung auf physischem iPad und keine Sicherheitsfreigabe.

## Nächster Gerätetest

1. Erledigt: Xcode 27.0 und iOS-/iPadOS-27-Simulatorruntime installiert.
2. Erledigt: Separate Qt/PySide-6.12-iOS-Umgebung mit passenden PySide-/Shiboken-Wheels
   und Python.xcframework bereitstellen; produktive Mac-Buildumgebung nicht ändern.
3. Erledigt: Mit pyside6-ios-deploy main.py als eigenes Xcode-Projekt generieren.
   Eigene Bundle-ID: de.jenaplan.kompetenzmanager.ipad-prototype.
4. Simulator bestanden; noch offen: signiertes Build auf echtem iPad:
   alle drei Auswahlen speichern, App schließen und erneut öffnen;
   Zustand muss erhalten bleiben. Hochformat, Querformat und Touch prüfen.
5. Python-sqlite3 und eigene Containerdatei im Simulator nachgewiesen.
   Apples Dateischutzattribute und Sperrverhalten sind noch nicht implementiert
   oder geprüft; der Prototyp ist keine Sicherheitsfreigabe.
6. Danach Pflanzen-PDF und natives Teilen ergänzen. ReportLab/Pillow sind in
   diesem ersten Prototyp absichtlich nicht enthalten; deren iOS-Build bleibt offen.

Kein Backup, Import, Kontowechsel, Produkt-Restore oder Sparkle-Updater.
Keine automatische Installation von Xcode oder Änderung der globalen Toolchain.

Offizielle Voraussetzungen:
https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-ios-deploy.html

## Historie: erster Build vor Mac-Neustart 11.10.2026

Offizielle Qt-6.12.0 ARM64-Simulator-Wheels und die vom Qt-Tool hashgeprüfte
Python-3.15.0rc2-iOS-XCframework-Runtime. Getrennte Hostumgebung unter
/private/tmp/jkm-ipad-build-venv; Buildquelle ist eine Kopie dieses main.py.
Xcode-Projekt automatisch mit pyside6-ios-deploy erzeugt, eigene Bundle-ID
de.jenaplan.kompetenzmanager.ipad-prototype. Simulator-Build erfolgreich mit
ARCHS=arm64 ONLY_ACTIVE_ARCH=YES CODE_SIGN_IDENTITY=-. Der allgemeine
Simulator-Build versucht auch x86_64, was nicht zu diesen Wheels passt;
CODE_SIGNING_ALLOWED=NO verhindert das erforderliche Signieren der
Python-Erweiterungsframeworks und ist hierfür ungeeignet.

Arbeitsverzeichnis: /private/tmp/jkm-ipad-build/app. Erzeugtes Projekt:
deployment/ios_arm64_simulator/Jenaplan-iPad-Test.xcodeproj.
Buildlog: /private/tmp/jkm-ipad-build/xcodebuild-signed.log.
Eigener synthetischer Simulator: 35D6A4A6-3200-45FF-AE8E-3E3B45F5FA18.
Appstart und echte Persistenzprüfung im Simulator sind noch ausstehend: drei Starts
des eigenen Simulators bleiben vor erfolgreicher Installation hängen. Device Hub
meldet Connection timed out / DeviceKitError 4002; simctl install wartet bzw.
endet bei kontrolliertem Shutdown mit Mach error -308. Kein App-Code-Fehler
bewiesen. Nach Installation der neuen Xcode-Komponenten ist ein Mac-Neustart
der nächste sinnvolle Infrastrukturversuch; noch kein iPad-Lauffähigkeitsnachweis.
Kompaktbelege und erfolgreicher Buildlog unter output/ipad-prototype/.

## Fortsetzung nach Mac-Neustart

Das System-Temporärverzeichnis wurde beim Neustart entfernt. Der reproduzierte
Buildarbeitsordner liegt jetzt dauerhaft unter output/ipad-prototype/build/,
das separate Host-Venv unter output/ipad-prototype/venv/. Download-Wheels sind
gegen die vor dem Neustart gespeicherten SHA256 geprüft; Quellkopie unverändert.
Neues Buildlog: output/ipad-prototype/xcodebuild-after-reboot.log.
Der eigene Simulator zeigt nach dem Neustart den iPadOS-Startbildschirm.
Erneutes Packaging, Installation und Start erfolgreich. Oberflächenauswahl,
SQLite-Speicherung und Wiederöffnung sowie beide Ausrichtungen bestanden.
Lokale Belege: build-inputs.json, build-evidence.json und
simulator-persistence.json unter output/ipad-prototype/.
Die Buildquelle ist bytegleich mit main.py aus Commit f48ee76; keine Codeänderung
für diesen Wiederholungsversuch. Der Prototyp bleibt im eigenen Simulator offen.
