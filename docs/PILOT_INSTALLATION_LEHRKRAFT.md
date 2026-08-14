# Installation des Jenaplan-Kompetenzmanagers

Diese Anleitung gilt für den vorbereiteten Final-V4-Pilotstand Version
{{PILOT_VERSION}} / Build {{PILOT_BUILD}}. Sie ist noch kein finales App-Bundle
oder Releaseartefakt.

## 1. Voraussetzungen

> [!VORAUSSETZUNG]
> - Mac mit Apple-Prozessor (M1 oder neuer) und macOS 13 oder neuer;
> - ungefähr 300 MB freier Speicherplatz für App und erste lokale Daten;
> - die vereinbarte DMG-Datei.

Die App arbeitet lokal, ohne Cloud und ohne KI-Verarbeitung von Fachdaten.
Fachdaten und verwaltete Dokumente werden lokal verschlüsselt gespeichert.

## 2. App installieren

1. Das vereinbarte DMG im Finder öffnen.
2. `Jenaplan-Kompetenzmanager.app` in `Programme` ziehen.
3. Das Kopieren abwarten und das DMG auswerfen.
4. Die App aus `Programme` öffnen.
5. Unter `Über die App` Version {{PILOT_VERSION}} und Build {{PILOT_BUILD}}
   prüfen.

Python, Terminal und Repository werden nicht benötigt.

## 3. Gatekeeper kontrolliert freigeben

Der aktuelle interne Pilotvertrag ist ad-hoc signiert und nicht notarisiert.
macOS kann den ersten Start deshalb blockieren.

1. Den macOS-Hinweis schließen.
2. Im Ordner `Programme` mit gedrückter Control-Taste auf die App klicken.
3. `Öffnen` wählen und bestätigen.
4. Falls nötig, unter `Systemeinstellungen > Datenschutz & Sicherheit` nur für
   diese App `Dennoch öffnen` wählen.

> [!WARNUNG]
> Gatekeeper niemals global deaktivieren. Es werden keine Apple-Zugangsdaten,
> Zertifikate oder Kennwörter mitgeliefert.

## 4. Erster Start

Beim ersten Start ein App-Passwort mit mindestens 15 Zeichen anlegen. Das
Passwort schützt den Zugang; der eigentliche Datenschlüssel ist davon getrennt
und wird über den macOS-Schlüsselbund geschützt. Die einmalig angezeigten
Recovery-Codes getrennt und außerhalb des Macs sicher aufbewahren.

Die App richtet einen frischen verschlüsselten Final-V4-Produktbereich ein.
Automatisch vorhanden sind:

- Schuljahr `2026/27` vom 01.08.2026 bis 31.07.2027;
- offizielles Entwicklungsbuch;
- 331 Kompetenzen.

Nicht automatisch vorhanden sind Schüler, Stammgruppen, Kurse, Kursverbünde,
Beobachtungen, Bestätigungen, Berichtsentwürfe, LEG-Entwürfe, Testdokumente,
Beispielschüler, Beispielbeobachtungen oder Testbackups. Ein Beispielbestand
ist für den Pilotstart nicht erforderlich.

## 5. Backup, Restore und Unterstützung

Unter `Einstellungen > Datensicherung` ein verschlüsseltes `.jkmebackup`
erstellen und prüfen. Restore prüft das Backup, zeigt eine Vorschau und
verlangt eine ausdrückliche Bestätigung. Danach folgen verifiziertes Staging,
Safety-Backup, separater Worker, vollständige App-Beendigung, kontrollierter
Neustart und erneute Anmeldung.

Das Backup bleibt an die ursprüngliche geschützte Installation und deren
vorhandenen lokalen Schlüsselkontext gebunden. Es kann nicht beliebig auf jedem
Mac wiederhergestellt werden und ist kein Cloud-Backup.

Recovery-Codes sind der erste Wiederherstellungsweg. Support Reset ist nur ein
betreuter Ausnahmeweg, wenn Passwort und Recovery-Codes fehlen, die
ursprüngliche Installation mit zugreifbarem lokalem Schlüssel vollständig
intakt ist und ein neues Safety-`.jkmebackup` erfolgreich erstellt und geprüft
werden kann. Support erhält weder Passwort noch Schülerdaten oder
Backupinhalt. Ein verlorener lokaler Datenschlüssel ist nicht recoverbar.

## 6. Bekannte Grenzen

> [!HINWEIS]
> - keine Windows-Freigabe, kein öffentlicher Stable-Release;
> - ad-hoc signiert, nicht notarisiert; Developer ID bleibt separat;
> - keine Cloud-Synchronisation oder KI-Funktion;
> - keine automatische Migration älterer lokaler Produktbestände;
> - keine allgemeine Geräteportabilität oder Recovery eines verlorenen
>   lokalen Datenschlüssels;
> - finale Bericht- und LEG-PDFs öffnen read-only im sicheren In-App-Viewer;
>   Export, Drucken und Teilen sind nicht Teil dieses Vertrags.
