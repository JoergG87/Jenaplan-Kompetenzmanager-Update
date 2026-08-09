# Installation des Jenaplan-Kompetenzmanagers

Diese Anleitung gilt für den internen macOS-arm64-Stand Version
{{PILOT_VERSION}} / Build {{PILOT_BUILD}}. Sie wird zusammen mit einem späteren
DMG übergeben; dieses Dokument belegt selbst kein bereits erzeugtes DMG.

## 1. Voraussetzungen

> [!VORAUSSETZUNG]
> - Mac mit Apple-Prozessor (M1 oder neuer) und macOS 13 oder neuer;
> - ungefähr 300 MB freier Speicherplatz für App und erste lokale Daten;
> - die vereinbarte DMG-Datei des Jenaplan-Kompetenzmanagers.

Die App arbeitet lokal. Sie überträgt keine Fachdaten in eine Cloud und nutzt
keine KI-Funktion.

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

Der interne Build ist ad-hoc signiert und nicht notarisiert. macOS kann beim
ersten Start warnen.

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
Recovery-Codes getrennt vom Mac aufbewahren. Die App richtet ihren lokalen
Datenbereich ein; vorhandene Fachdaten werden nicht durch Beispiel- oder
Pilotdaten ersetzt.

Nach dem Anmelden können unter `Einstellungen > Sicherheit` die gespeicherte
Geräteanmeldung und bei erfüllten Voraussetzungen Touch ID eingerichtet werden.
Die Oberfläche erklärt sichtbar, wenn Hardware, Einrichtung, Credential oder
Secret fehlen. Das Passwort bleibt immer der Fallback. Die App sperrt sich
automatisch.

## 5. Backup, Restore und Unterstützung

Vor einem Update ein geprüftes lokales `.jkmebackup` erstellen. Der aktuelle
Produktpfad verwendet ausschließlich den verschlüsselten Final-V4-Container.
Die Restore-Vorschau lesen und
`Wiederherstellung starten` nur bewusst wählen: die App erstellt vorher ein
Sicherheitsbackup, übergibt an einen separaten Restore-Worker, beendet sich
vollständig und startet kontrolliert neu. Danach erneut anmelden und
Fachdaten prüfen.

Startet der Worker nicht, bleibt der bisherige aktive Bestand unverändert. Ein
Das Backup ist verschlüsselt, aber an dieselbe Installation und deren DMK
gebunden. Zusätzliches externes, schulisch geregeltes Backup bleibt sinnvoll;
ein Gerätewechsel oder DMK-Verlust ist damit nicht gelöst.

Support-Reset bleibt im Cipher-Modus kontrolliert blockiert, solange seine vor
Authentifizierung nötige sichere Backup-Komposition nicht freigegeben ist.

## 6. Bekannte Grenzen

> [!HINWEIS]
> - keine Windows-Freigabe und kein öffentlicher Stable-Release;
> - keine Notarisierung und kein Developer-ID-Nachweis;
> - keine Cloud-Synchronisation oder KI-Funktion;
> - keine Migration bestehender Klartext- oder Altbestände; ausschließlich ein
>   frischer verschlüsselter Final-V4-Bestand;
> - keine automatische Update-, Download- oder Installationsaktion.

Das ausführliche Benutzerhandbuch und
`SICHERHEIT_UND_VERSCHLUESSELUNG.md` beschreiben Bedienung, Schutzgrenzen und
Verantwortlichkeiten der Schule.
