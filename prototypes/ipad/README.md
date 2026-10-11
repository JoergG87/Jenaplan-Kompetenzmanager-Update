# iPad-Machbarkeitstest

Separater Prototyp, kein Produktbuild. Drei feste synthetische Kompetenzen,
explizite Auswahl, Standard-SQLite und Wiederöffnung. Keine realen Schülerdaten,
keine Produktmodule, kein Zugriff auf Mac-Produktdaten oder Schlüssel.
Die Testtabelle verändert das Produktdatenmodell nicht.

## Aktueller Nachweis

Repository-Tests bestehen auf macOS: Speicherung und Wiederöffnung,
ungültige Auswahl ohne Änderung, Abweisung fremder Datenbanken und Symlinks.
Ein Offscreen-Test prüft Auswahl und Speicherung über das Fenster.
Dies beweist weder iPad-Packaging noch iPad-Bedienung oder Dateischutz.

## Nächster Gerätetest

1. Erledigt: Xcode 27.0 und iOS-/iPadOS-27-Simulatorruntime installiert.
2. Separate Qt/PySide-6.12-iOS-Umgebung mit passenden PySide-/Shiboken-Wheels
   und Python.xcframework bereitstellen; produktive Mac-Buildumgebung nicht ändern.
3. Mit pyside6-ios-deploy main.py als eigenes Xcode-Projekt generieren.
   Eigene Bundle-ID: de.jenaplan.kompetenzmanager.ipad-prototype.
4. Zunächst Simulator, anschließend signiertes Build auf echtem iPad:
   alle drei Auswahlen speichern, App schließen und erneut öffnen;
   Zustand muss erhalten bleiben. Hochformat, Querformat und Touch prüfen.
5. Python-sqlite3-Verfügbarkeit und Dateien im eigenen App-Container nachweisen.
   Apples Dateischutzattribute und Sperrverhalten sind noch nicht implementiert
   oder geprüft; der Prototyp ist keine Sicherheitsfreigabe.
6. Danach Pflanzen-PDF und natives Teilen ergänzen. ReportLab/Pillow sind in
   diesem ersten Prototyp absichtlich nicht enthalten; deren iOS-Build bleibt offen.

Kein Backup, Import, Kontowechsel, Produkt-Restore oder Sparkle-Updater.
Keine automatische Installation von Xcode oder Änderung der globalen Toolchain.

Offizielle Voraussetzungen:
https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-ios-deploy.html

## Buildnachweis 11.10.2026

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
