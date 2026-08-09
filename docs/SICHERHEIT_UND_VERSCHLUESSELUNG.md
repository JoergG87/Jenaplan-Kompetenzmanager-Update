# Sicherheit und Verschlüsselung

Stand: 9. August 2026
Geltung: neuer Cipher-Pilot-Quellstand; noch kein neu gebautes Produktartefakt
Status: Technische Produktkomposition aktiviert, manuelle und paketierte Abnahme offen

Dieses Dokument beschreibt den tatsächlich aktiven Schutzstand und die bewusst
noch nicht aktivierte Verschlüsselungsintegration. Es ist keine
Datenschutzfreigabe, keine Rechtsberatung und keine Aussage
„DSGVO-konform“ oder „vollständig sicher“.

## 1. Überblick

Der Jenaplan-Kompetenzmanager ist eine lokale Desktop-App für macOS auf Apple
Silicon (arm64). Er überträgt keine fachlichen Daten in eine Cloud und bindet
keine KI-Dienste ein. Schülerdaten, Beobachtungen, Anhänge, Berichte,
Lernentwicklungsgespräche und PDF-Ausgaben haben deshalb einen hohen
Schutzbedarf.

Ein späterer GitHub-Pre-Release/Pilot für 0.3.0 / Build 303 auf macOS wird
ad-hoc signiert und nicht notarisiert sein. Es gibt keine Windows-Freigabe,
keinen Stable-Release und keinen Stable-Appcast. Ein konkretes DMG, seine
Prüfsumme und der zugehörige Buildcommit werden ausschließlich aus dem Clean-Build als
Releaseartefakte nachgewiesen.

## 2. Heute aktiv geschützt

Im normalen Produktpfad sind folgende Schutzfunktionen aktiv:

> [!SICHERHEIT]
> - lokales Passwort mit erster Passwortanlage, Bestätigung und
>   Passwortänderung;
> - Recovery-Codes als erster Wiederherstellungsweg;
> - optionales Gerätecredential im macOS-Schlüsselbund für die Komfortanmeldung;
> - optionales Touch ID bei erfüllten Voraussetzungen;
> - sichtbare Gründe, wenn Touch ID nicht eingerichtet, nicht verfügbar oder
>   vorübergehend gesperrt ist;
> - immer verfügbarer Passwort-Fallback;
> - automatische App-Sperre nach Inaktivität oder Ruhezustand sowie
>   Jetzt sperren;
> - betreuter Support-Reset mit zeitlich begrenztem, installationsgebundenem
>   Code; sein bisheriges ZIP-v1-Sicherheitsbackup ist im Cipher-Modus bis zum
>   Folgepaket gesperrt;
> - exakt SQLCipher 4.17/CommonCrypto für die frische Final-V3-Datenbank und
>   den Dokument-Companion;
> - verschlüsselte Managed-Document-Container für Anhänge, allgemeine
>   Schülerdokumente sowie finale Bericht-/LEG-PDFs;
> - getrennte lokale Runtime-Bereiche, restriktive Dateirechte und kein
>   Zugriff auf den fachlichen Bestand vor erfolgreicher Anmeldung.

Die App-Sperre schützt zusätzlich die Oberfläche vor unbefugter Nutzung im
laufenden Alltag. Sie ersetzt nicht die separate Datenverschlüsselung. Backup
und Restore sind im Cipher-Produktmodus derzeit keine freigegebene Funktion.

### Signierung und Updates

Der GitHub-Pre-Release/Pilot für macOS wird ad-hoc signiert. Das hilft bei der
Integritätszuordnung des erzeugten Artefakts, ersetzt aber weder Developer ID
noch Apple-Notarisierung. Es ist kein öffentlicher Updatekanal aktiv. Signierte
Updateartefakte werden deshalb nicht als aktive Schutzfunktion für den
normalen Produktbetrieb behauptet.

## 3. Aktuelle Datenhaltung

Die App hält ihre Daten lokal und getrennt vom App-Bundle:

- Die fachliche Final-V3-SQLCipher-Datenbank enthält den fachlichen Bestand.
- Ein keyed SQLCipher-Companion registriert verschlüsselte
  Managed-Document-Container im lokalen App-Datenbereich.
- Ein separater Security Store enthält Anmelde- und Security-Metadaten.
- Der lokale Backupbereich ist registriert; Cipher-Backup/-Restore ist bis zum
  Folgepaket technisch deaktiviert.
- Frei exportierte Entwurfs-PDFs und andere bewusst abgelegte Ausgaben liegen
  außerhalb der App und müssen wie vertrauliche Schulunterlagen behandelt
  werden.

Dieses Dokument nennt absichtlich keine Entwicklerpfade, Secrets, Keychain-
Einträge oder konkrete lokale Kennungen. Technische Betreuung soll nur die
zuständige lokale Datenablage nach der jeweils freigegebenen
Installationsanleitung verwalten.

## 4. Verschlüsselungsstatus

Die Security- und Verschlüsselungsfoundations sind implementiert. Der normale
neue Pilotstart aktiviert davon nach erfolgreicher Authentifizierung die
frische Final-V3-SQLCipher-Runtime, den keyed Companion und verschlüsselte
Dokumentcontainer:

> [!HINWEIS]
> - Verbindlich sind Binding `0.6.2+jkm.sqlcipher4170.1`, SQLCipher
>   `4.17.0 community`, SQLite `3.53.3` und CommonCrypto.
> - Eine andere oder fehlende Engine sowie Standard-SQLite blockieren den
>   Start fail-closed.
> - Bestehende Pilot- und Produktdaten werden nicht automatisch zu SQLCipher
>   migriert.
> - Bestehende Klartextdokumente werden nicht still in verschlüsselte
>   Container überführt.
> - Cipher-Backup/-Restore und der alte ZIP-v1-Pfad bleiben produktiv
>   gesperrt.

Es gibt absichtlich keine Produktmigration. Reale Keychain-, UI-, Build- und
Paketabnahme sowie Cipher-Backup/-Restore bleiben gesonderte Freigabegates.

## 5. Schlüsselarchitektur in verständlicher Form

Die aktive Anmeldung und die vorbereitete Verschlüsselungsarchitektur haben
unterschiedliche Aufgaben.

- Das lokale Passwort authentifiziert die Lehrkraft; es ist nicht der
  Datenbankschlüssel.
- Der Data Master Key (DMK) liegt als separates Secret im macOS-Schlüsselbund.
- Ein zufälliger Database-Key liegt nur in einem mit dem DMK authentisierten
  Envelope und öffnet Haupt- sowie Companion-Datenbank.
- Dokumente erhalten getrennte zufällige Document-Keys; die vorbereitete
  Backup-Key-Domäne ist noch nicht produktiv aktiviert.
- Passwortwechsel und Support-Reset ändern das Passwort und die
  Anmeldeinformationen, ersetzen aber nicht den DMK.
- Schlüssel, Passwörter, Recovery-Codes und vollständige Reset-Codes gehören
  weder in Logs noch in fachliche Backups.

Diese Architektur ist absichtlich nur bis zu der Tiefe beschrieben, die für
schulische technische Betreuung erforderlich ist. Kryptografische Formate,
Schlüsselhüllen, Ableitungen, Authentisierung und
Migrationszustandsautomaten sind in den bestehenden technischen ADRs,
insbesondere ADR-075 bis ADR-093 und ADR-088, dokumentiert. Dieses Dokument
dupliziert diese Details nicht.

## 6. Backup und Restore

Backup und Restore sind im Cipher-Produktmodus technisch gesperrt. Die
vorhandenen UI-Aktionen zeigen `Noch nicht verfügbar.`; Restore-Worker,
Resume, Schuljahreswechsel-Backup und Support-Reset-Backup dürfen ZIP-v1 nicht
auf den Cipherbestand anwenden. Die vorbereitete `.jkmebackup`-Runtime und der
verschlüsselte Restore-Stand werden erst in einem Folgepaket produktiv
komponiert.

Es gibt in diesem Paket keinen fachlichen Austausch, keine Konvertierung und
keine Wiederaufnahme eines Restore-Vorgangs.

### Grenzen

> [!WARNUNG]
> ZIP-v1 darf nicht auf den Cipherbestand angewendet werden. Ein
> verschlüsselter Backupcontainer existiert als noch nicht produktiv
> aktivierte Foundation. Vor einer Pilotübergabe ist deshalb ein separat
> freigegebener Cipher-Backup-/Restorepfad erforderlich.

## 7. Bedrohungsmodell

### Gegen welche Risiken dieser Stand schützt

Die aktivierte lokale Datenverschlüsselung verbessert insbesondere den Schutz
gegen:

- kopierte Datendateien;
- kopierte Final-V3-, Companion- und Dokumentcontainerdateien;
- verlorene Geräte;
- manipulierte oder beschädigte Artefakte;
- unvollständige oder widersprüchliche Cipher-Runtimezustände beim Startup.

Passwort, App-Sperre, Schlüsselbund, Touch ID und lokale Dateirechte ergänzen
diesen Schutz. Backup, Restore, Gerätewechsel und DMK-Recovery sind dadurch
nicht gelöst.

### Was nicht vollständig abgedeckt ist

Weder der aktuelle noch ein später verschlüsselter lokaler Produktpfad schützt
vollständig gegen:

- Malware unter demselben macOS-Benutzerkonto;
- Speicheranalyse eines laufenden Prozesses;
- Keylogger;
- Screenshots;
- hochprivilegierte lokale Angreifer;
- eine garantierte physische Löschung von SSD-Daten.

Ein verlorenes Gerät bleibt ein meldepflichtiger Sicherheitsvorfall. Die
vorbereitete Verschlüsselung reduziert dieses Risiko erst nach einer
kontrollierten, nachweisbaren Produktaktivierung.

## 8. Verantwortlichkeiten der Schule

Schule, technische Betreuung und Lehrkräfte tragen gemeinsam Verantwortung für
den sicheren Betrieb:

- Nur schulisch freigegebene Geräte und sichere lokale Benutzerkonten einsetzen.
- macOS-Gerätesperre sowie FileVault nach Schulvorgabe aktivieren.
- Keine gemeinsamen Benutzerkonten verwenden.
- Externe Backups regelmäßig erstellen, prüfen und nach Schulvorgabe
  aufbewahren.
- Keine Schülerdaten in Screenshots, Testdaten, Tickets oder frei zugängliche
  Ablagen übernehmen.
- Exportierte und finale PDFs nur über sichere schulische Wege weitergeben.

Technische Betreuung unterstützt bei Installationsfreigabe, Recovery und
Sicherungsstrategie. Sie kennt nicht automatisch das Lehrkraftpasswort und
erhält durch einen Support-Reset keinen Zugang zu den fachlichen Daten.

## 9. Plattform- und Releasegrenzen

Für 0.3.0 / Build 303 gilt:

- ad-hoc signiert;
- nicht notarisiert;
- Apple Developer ID und Notarisierung offen;
- macOS arm64 als Zielplattform;
- Windows ungeprüft, kein DPAPI-Produktpfad;
- GitHub-Pre-Release/Pilot, keine Stable-Freigabe;
- kein Stable-Appcast und kein automatischer Pilotrollout.

> [!WARNUNG]
> Gatekeeper-Hinweise werden ausschließlich über den kontrollierten macOS-Weg
> für die konkrete interne App freigegeben. Gatekeeper darf nicht global
> deaktiviert werden.

## 10. Offene Schritte

Folgende Arbeiten sind bewusst nicht Teil dieses Dokumentations- und
Build-303-Vorbereitungsstands:

- kontrollierte Produktmigration bestehender Fachdaten;
- Pilotaktivierung und Abnahme der Verschlüsselung;
- verständliche Recovery-Nutzerführung für verschlüsselte Bestände;
- Windows- und DPAPI-Implementierung samt echter E2E-Abnahme;
- Apple Developer ID, Notarisierung und die zugehörigen
  Gatekeeper-Nachweise;
- reale Power-Loss-Abnahme auf Zielhardware;
- Freigabe eines öffentlichen Stable-Release.

Bis zu diesen Nachweisen sind die Datenverschlüsselungsfoundations keine aktive
Produktfunktion und der Stand ist nicht als vollständig sicher oder
datenschutzrechtlich vollständig freigegeben zu verstehen.

### Bei Verdacht oder Datenverlust

1. Verlust eines Geräts, unerwartete Passwort- oder Reset-Ereignisse und
   Verdacht auf Manipulation unverzüglich melden.
2. Datenbereiche nicht manuell verschieben, löschen oder mit Fremdwerkzeugen
   bearbeiten, solange ein Backup, Restore oder Support-Reset läuft.
