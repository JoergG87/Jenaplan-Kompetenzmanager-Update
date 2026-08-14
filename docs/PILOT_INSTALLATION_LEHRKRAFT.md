# Installation des Jenaplan-Kompetenzmanagers

Diese Anleitung gilt für den vorbereiteten macOS-arm64-Pilotstand Version
{{PILOT_VERSION}} / Build {{PILOT_BUILD}}. Sie wird zusammen mit einem später
freigegebenen DMG übergeben; dieses Dokument belegt weder ein bereits erzeugtes
DMG noch Pilot-GO, Verteilung oder Release.

## 1. Voraussetzungen

> [!VORAUSSETZUNG]
> - Mac mit Apple-Prozessor (M1 oder neuer) und macOS 13 oder neuer;
> - ungefähr 300 MB freier Speicherplatz für App und erste lokale Daten;
> - die vereinbarte DMG-Datei des Jenaplan-Kompetenzmanagers.

Die App arbeitet lokal. Sie überträgt keine Fachdaten in eine Cloud und nutzt
keine KI-Funktion. Fachdaten und verwaltete Dokumente werden lokal
verschlüsselt gespeichert.

## 2. App aus dem DMG installieren

1. Das vereinbarte DMG im Finder öffnen.
2. `Jenaplan-Kompetenzmanager.app` in den Ordner `Programme` ziehen.
3. Das Kopieren vollständig abwarten und das DMG im Finder auswerfen.
4. Die App im Ordner `Programme` regulär öffnen.
5. Unter `Über die App` Version {{PILOT_VERSION}} und Build {{PILOT_BUILD}}
   prüfen.

Für den normalen Start sind weder Python, Terminal noch ein Repository nötig.
Die `.command`-Datei ist ausschließlich ein Entwicklerwerkzeug und kein
Installationsweg.

## 3. Gatekeeper-Hinweis kontrolliert freigeben

Für 0.4.0 / Build 400 sind Developer-ID-Signierung und Notarisierung noch nicht
nachgewiesen. Ein internes Artefakt kann beim ersten Start von macOS blockiert
werden.

1. Den Hinweis schließen.
2. Im Ordner `Programme` mit gedrückter Control-Taste auf die App klicken.
3. `Öffnen` wählen und den Start bestätigen.
4. Falls macOS weiter blockiert, unter `Systemeinstellungen > Datenschutz &
   Sicherheit` nur für diese App `Dennoch öffnen` wählen.

> [!WARNUNG]
> Gatekeeper niemals global deaktivieren. Es werden keine Apple-Zugangsdaten,
> Zertifikate oder Kennwörter mitgeliefert.

## 4. Erster Start und lokale Anmeldung

Beim ersten Start erscheint `Lokales Konto einrichten`. Ein Passwort mit
mindestens 15 Zeichen festlegen, bestätigen und die einmalig angezeigten
Recovery- und Sicherheitsinformationen getrennt vom Mac aufbewahren. Die App
richtet einen frischen verschlüsselten Datenbereich ein. Sie erzeugt nur das
aktuelle Schuljahr `2026/27`; Schüler, Gruppen, Kurse, Beobachtungen und
Testdaten werden nicht automatisch angelegt.

Nach dem Anmelden können unter `Einstellungen > Sicherheit` die gespeicherte
Geräteanmeldung und bei erfüllten Voraussetzungen Touch ID eingerichtet werden.
Die Oberfläche erklärt sichtbar, wenn Hardware, Einrichtung, Credential oder
Secret fehlen. Das Passwort bleibt immer der Fallback. Die App sperrt sich
automatisch.

## 5. Backup, Restore und Unterstützung

Vor einem Update ein geprüftes lokales `.jkmebackup` erstellen. Die
Restore-Vorschau lesen und `Wiederherstellung starten` nur bewusst wählen. Die
App prüft das Backup vollständig in einem getrennten Vorbereitungsbereich,
erstellt vor dem Austausch ein Sicherheitsbackup, übergibt an einen separaten
Restore-Worker, beendet sich vollständig und startet kontrolliert neu. Danach
erneut anmelden und Fachdaten prüfen. Bei einem Fehler wird der bisherige
Bestand beibehalten beziehungsweise kontrolliert zurückgesetzt.

Startet der Worker nicht, bleibt der bisherige aktive Bestand unverändert. Das
Backup ist verschlüsselt, aber an dieselbe Installation und deren vorhandenen
Installationsschlüssel gebunden. Zusätzliches externes, schulisch geregeltes
Backup bleibt sinnvoll; ein Gerätewechsel oder Schlüsselverlust ist damit
nicht gelöst.

Support-Reset ist ausschließlich auf der ursprünglichen intakten Installation
mit zugreifbarem Installationsschlüssel möglich. Die App prüft den vorhandenen
Final-V4-Bestand vollständig und erzeugt und verifiziert ein verschlüsseltes
Safety-Backup, bevor sie nur den Authentifizierungszustand zurücksetzt.

## 6. Bekannte Grenzen

> [!HINWEIS]
> - keine Windows-Freigabe und kein öffentlicher Stable-Release;
> - keine Notarisierung und kein Developer-ID-Nachweis;
> - keine Cloud-Synchronisation oder KI-Funktion;
> - keine automatische Migration bestehender alter lokaler Datenbestände;
>   für den kommenden Pilot werden keine produktiven Altdaten vorausgesetzt;
> - Support-Reset hilft nur bei verlorenen Anmeldedaten auf der weiterhin
>   intakten ursprünglichen Installation; verlorene Installationsschlüssel und
>   Gerätewechsel bleiben nicht wiederherstellbar;
> - finale Bericht- und LEG-PDFs können im gemeinsamen sicheren In-App-Viewer
>   gelesen werden; Export, Drucken und Teilen sind nicht verfügbar;
> - keine automatische Update-, Download- oder Installationsaktion.

Das ausführliche Benutzerhandbuch und
`SICHERHEIT_UND_VERSCHLUESSELUNG.md` beschreiben Bedienung, Schutzgrenzen und
Verantwortlichkeiten der Schule.
