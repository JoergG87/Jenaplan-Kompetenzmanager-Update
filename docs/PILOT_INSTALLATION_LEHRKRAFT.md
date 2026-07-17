# Installation des Jenaplan-Kompetenzmanagers - Pilotversion

Diese Anleitung begleitet Sie von der Installationsdatei bis zum ersten Start.
Die Pilotversion arbeitet ausschließlich auf diesem Mac und überträgt keine Daten
automatisch in eine Cloud.

## 1. Voraussetzungen

- Mac mit Apple-Prozessor (M1 oder neuer)
- macOS 13 oder neuer
- ungefähr 300 MB freier Speicherplatz für App und erste lokale Daten
- die Datei `Jenaplan-Kompetenzmanager-{{PILOT_VERSION}}-macOS-arm64.dmg`

Die Version {{PILOT_VERSION}} ist eine Pilotversion. Sie ist für den vereinbarten Test gedacht
und besitzt noch keinen automatischen Aktualisierungsdienst.

## 2. Installation

1. Öffnen Sie die DMG-Datei mit einem Doppelklick.
2. Ziehen Sie `Jenaplan-Kompetenzmanager` auf den Ordner `Programme`.
3. Warten Sie, bis der Kopiervorgang beendet ist.
4. Werfen Sie das geöffnete Laufwerk im Finder aus.
5. Öffnen Sie den Ordner `Programme` und starten Sie dort den
   `Jenaplan-Kompetenzmanager`.

Für den normalen Start sind keine zusätzlichen Programme erforderlich.

## 3. macOS-Sicherheitshinweis

Diese lokale Pilotversion ist noch nicht über den App Store verteilt und nicht
von Apple bestätigt. macOS kann deshalb beim ersten Start den Hinweis anzeigen,
dass die App von einem unbekannten Entwickler stammt.

Gehen Sie in diesem Fall so vor:

1. Schließen Sie den Hinweis.
2. Klicken Sie im Ordner `Programme` mit gedrückter Control-Taste auf den
   `Jenaplan-Kompetenzmanager`.
3. Wählen Sie `Öffnen` und bestätigen Sie den Start.
4. Falls macOS weiterhin blockiert, öffnen Sie
   `Systemeinstellungen > Datenschutz & Sicherheit` und wählen Sie beim Hinweis
   zum Jenaplan-Kompetenzmanager `Dennoch öffnen`.

Verwenden Sie nur die Pilotdatei aus der vereinbarten Übergabe. Deaktivieren Sie
nicht allgemein die Schutzfunktionen Ihres Macs.

## 4. Erster Start

Beim ersten Start legt die App ihren geschützten lokalen Datenordner automatisch
an. Vorhandene Daten werden dabei nicht überschrieben.

Der Release-Kandidat startet ohne Kinder, Pilotdaten und Dokumente. Nach dem
Anlegen des lokalen Kontos werden Recovery-Codes einmalig angezeigt. Bewahren
Sie diese getrennt und sicher auf. Die geführten `Ersten Schritte` unterstützen
bei der Einrichtung; sie legt selbst keine Daten an.

Die App-Sperre ist keine Verschlüsselung der Datenbank, Dokumente oder Backups.
FileVault und ein geschütztes macOS-Benutzerkonto werden empfohlen.

## 5. Update der Pilotversion

1. Schließen Sie den Jenaplan-Kompetenzmanager vollständig.
2. Erstellen Sie nach Möglichkeit vorher die vereinbarte Sicherung.
3. Öffnen Sie das neue DMG.
4. Ziehen Sie die neue App wieder auf `Programme` und bestätigen Sie `Ersetzen`.
5. Starten Sie die App erneut.

Die lokalen Daten liegen getrennt von der App und bleiben beim Ersetzen erhalten.
Es gibt bewusst keinen automatischen Updater.

## 6. Fehler melden

Bitte notieren Sie bei einer Rückmeldung:

- die Testnummer aus der Pilottest-Excel-Datei;
- was Sie unmittelbar vor dem Problem getan haben;
- den genauen Wortlaut einer Fehlermeldung;
- ob das Problem nach einem Neustart erneut auftritt.

Ein Screenshot hilft bei sichtbaren Darstellungs- oder Fehlermeldungen. Achten Sie
darauf, dass der Screenshot keine nicht vereinbarten personenbezogenen Daten zeigt.
