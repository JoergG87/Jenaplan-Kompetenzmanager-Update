# Sicherheit und Verschlüsselung

Stand: 14. August 2026
Geltung: Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}
Status: Inhaltlich finaler Final-V4-Reviewstand vor der Versionsanhebung;
noch kein finales Pilot-, Build- oder Releaseartefakt

Dieses Dokument beschreibt den tatsächlich aktiven committed Schutzstand und
die noch offene Build-/Realweltabnahme. Es ist keine
Datenschutzfreigabe, keine Rechtsberatung und keine Aussage
„DSGVO-konform“ oder „vollständig sicher“.

## 1. Überblick

Der Jenaplan-Kompetenzmanager ist eine lokale Desktop-App für macOS auf Apple
Silicon (arm64). Er überträgt keine fachlichen Daten in eine Cloud und bindet
keine KI-Dienste ein. Schülerdaten, Beobachtungen, Anhänge, Berichte,
Lernentwicklungsgespräche und PDF-Ausgaben haben deshalb einen hohen
Schutzbedarf.

Die angezeigte Version und der Build folgen der zentralen Produktversion. Diese
Reviewausgabe ist kein bereits verteiltes oder freigegebenes Release. Es gibt
noch keinen Nachweis für
Developer ID oder Notarisierung, keine Windows-Freigabe, keinen Stable-Release
und keinen Stable-Appcast. Ein konkretes DMG, seine Prüfsumme und der
zugehörige Buildcommit werden ausschließlich aus einem späteren sauberen Build
als Artefakte nachgewiesen.

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
> - Support-Reset im Cipher-Modus nur auf der ursprünglichen intakten
>   Installation, nach vollständiger lokaler Prüfung und verifiziertem
>   Safety-`.jkmebackup`;
> - exakt SQLCipher 4.17/CommonCrypto für die frische Final-V4-Datenbank und
>   den Dokument-Companion;
> - verschlüsselte Managed-Document-Container für Anhänge, allgemeine
>   Schülerdokumente sowie finale Bericht-/LEG-PDFs;
> - getrennte lokale Runtime-Bereiche, restriktive Dateirechte und kein
>   fachlicher Nutzer- oder Supportzugriff vor erfolgreicher Anmeldung; die
>   einzige Ausnahme ist der inhaltsfreie technische Support-Reset-Preflight
>   mit zwingendem Safety-Backup.

Die App-Sperre schützt zusätzlich die Oberfläche vor unbefugter Nutzung im
laufenden Alltag. Sie ersetzt nicht die separate Datenverschlüsselung. Backup
und Restore verwenden im Cipher-Produktmodus ausschließlich `.jkmebackup` und
bleiben auf dieselbe Installation gebunden.

Der Support-Reset fällt weder auf ZIP-v1 noch auf eine Klartext-Sicherung
zurück. Er ersetzt ausschließlich Authentifizierungs- und Recovery-Zustände;
DMK und Fachdaten-Schlüssel bleiben bestehen. Recovery-Codes bleiben der
vorgesehene erste Wiederherstellungsweg für das lokale Konto. Fehlt der
installationsgebundene DMK oder ist der lokale Final-V4-Bestand nicht
vollständig prüfbar, wird kein Reset durchgeführt.

### Signierung und Updates

Der aktuelle interne Pilotvertrag verwendet ad-hoc signierte, nicht
notarisierte Artefakte. Das ersetzt weder Developer ID noch Apple-
Notarisierung. Es ist kein öffentlicher Updatekanal aktiv.

## 3. Aktuelle Datenhaltung

Die App hält ihre Daten lokal und getrennt vom App-Bundle:

- Die fachliche Final-V4-SQLCipher-Datenbank enthält den fachlichen Bestand.
- Ein keyed SQLCipher-Companion registriert verschlüsselte
  Managed-Document-Container im lokalen App-Datenbereich.
- Der `ManagedDocumentStore` ist der zentrale Produktpfad für
  Beobachtungsanhänge, allgemeine Schülerdokumente sowie finale Bericht- und
  LEG-Artefakte. Fachliche Dokument-ID und physische Storage-Generation sind
  getrennt.
- Ein separater Security Store enthält Anmelde- und Security-Metadaten.
- Der lokale Backupbereich enthält ausschließlich `.jkmebackup`; Restore nutzt
  vollständige keyed Prüfung, neues Staging, Sicherheitsbackup,
  Worker-Handoff, kontrollierten Austausch, Rollback und Restart.
Finale verschlüsselte Bericht- und LEG-PDF-Artefakte öffnen über denselben
sicheren read-only In-App-Viewer. Python verifiziert und liefert die PDF-Bytes
nur für die flüchtige QtPdf-Anzeige im Speicher. Der Viewer unterstützt
mehrseitige Anzeige, Scrollen, Zoom, Schließen und erneutes Öffnen. Es gibt im
aktuellen finalen Artefaktpfad keine Klartextdatei, OS-Öffnung, Download,
Export-, Druck- oder Teilenfunktion.

Dieses Dokument nennt absichtlich keine Entwicklerpfade, Secrets, Keychain-
Einträge oder konkrete lokale Kennungen. Technische Betreuung soll nur die
zuständige lokale Datenablage nach der jeweils freigegebenen
Installationsanleitung verwalten.

## 4. Verschlüsselungsstatus

Die früheren Security- und Verschlüsselungsfoundations sind heute in den
normalen neuen Pilotstart integriert. Nach erfolgreicher Authentifizierung
werden die frische Final-V4-SQLCipher-Runtime, der keyed Companion und die
verschlüsselten Dokumentcontainer aktiv geöffnet:

> [!HINWEIS]
> - Verbindlich sind Binding `0.6.2+jkm.sqlcipher4170.1`, SQLCipher
>   `4.17.0 community`, SQLite `3.53.3` und CommonCrypto.
> - Eine andere oder fehlende Engine sowie Standard-SQLite blockieren den
>   Start fail-closed.
> - Bestehende Klartext-, V3- und alte Testbestände werden nicht automatisch
>   migriert. Für den kommenden Pilot gibt es keine produktiven Altdaten, die
>   übernommen werden müssten.
> - Bestehende Klartextdokumente werden nicht still in verschlüsselte
>   Container überführt.
> - Cipher-Backup/-Restore verwenden `.jkmebackup`; der alte ZIP-v1-Pfad bleibt
>   produktiv gesperrt.

Es gibt absichtlich keine Produktmigration. Reale Keychain-, UI-, Build-,
Paket- und Restore-Abnahme bleiben gesonderte Freigabegates.

## 5. Schlüsselarchitektur in verständlicher Form

Die aktive Anmeldung und die Datenverschlüsselung haben unterschiedliche
Aufgaben.

- Das lokale Passwort authentifiziert die Lehrkraft; es ist nicht der
  Datenbankschlüssel.
- Der Data Master Key (DMK) liegt als separates Secret im macOS-Schlüsselbund.
- Ein zufälliger Database-Key liegt nur in einem mit dem DMK authentisierten
  Envelope und öffnet Haupt- sowie Companion-Datenbank.
- Dokumente erhalten getrennte zufällige Document-Keys; `.jkmebackup` verwendet
  die getrennte Backup-Key-Domäne.
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

Backup und Restore sind im Cipher-Produktmodus auf `.jkmebackup` aktiviert.
Das Backup umfasst die keyed Final-V4-Datenbank, den keyed Companion,
notwendige Keyset-/Envelope-Metadaten und alle registrierten verschlüsselten
Dokumentgenerationen. Es enthält weder DMK noch App-Passwort, Recovery-Codes,
Touch-ID- oder Gerätecredentials.

Vor der Übernahme werden Container, Manifest, Final V4, Companion,
Schlüsselmetadaten, Bindungen und Dokumentgenerationen vollständig in einem
neuen Restore-Staging geprüft. Erst `RESTORE_READY` erlaubt die bewusste
Bestätigung. Danach folgen verschlüsseltes Sicherheitsbackup, separater
Restore-Worker, kontrollierter Austausch, Reopen/Neustart und Rollback bei
Fehlern. ZIP-v1 darf den Cipherbestand nie öffnen.

Der Restore ist installationsgebunden und benötigt den passenden bestehenden
DMK der Installation. Es gibt keinen Geräteübertragungs-, DMK-Recovery- oder
Klartextkonvertierungspfad.

### Grenzen

> [!WARNUNG]
> ZIP-v1 darf nicht auf den Cipherbestand angewendet werden. `.jkmebackup`
> ersetzt weder DMK-Recovery noch einen Gerätewechselpfad; beide bleiben offen.

## 7. Bedrohungsmodell

### Gegen welche Risiken dieser Stand schützt

Die aktivierte lokale Datenverschlüsselung verbessert insbesondere den Schutz
gegen:

- kopierte Datendateien;
- kopierte Final-V4-, Companion- und Dokumentcontainerdateien;
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

Ein verlorenes Gerät bleibt trotz aktiver lokaler Verschlüsselung ein
meldepflichtiger Sicherheitsvorfall.

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
- Finale PDFs ausschließlich über den vorgesehenen sicheren In-App-Viewer
  öffnen; es gibt in diesem Produktvertrag keine Export-, Druck- oder
  Teilenfunktion.

Technische Betreuung unterstützt bei Installationsfreigabe, Recovery und
Sicherungsstrategie. Sie kennt nicht automatisch das Lehrkraftpasswort und
erhält durch einen Support-Reset keinen Zugang zu den fachlichen Daten.

## 9. Plattform- und Releasegrenzen

Für Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}} gilt:

- noch kein freigegebenes oder verteiltes Buildartefakt;
- Developer-ID-Signierung nicht nachgewiesen;
- nicht als notarisiert freigegeben;
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

Folgende Arbeiten sind bewusst nicht mit diesem Dokumentationsstand
abgeschlossen:

- reale Pilot-, Bundle-, Keychain- und Restore-Abnahme der Verschlüsselung;
- Gerätewechsel- und DMK-Recovery;
- Windows- und DPAPI-Implementierung samt echter E2E-Abnahme;
- Apple Developer ID, Notarisierung und die zugehörigen
  Gatekeeper-Nachweise;
- reale Power-Loss-Abnahme auf Zielhardware;
- Freigabe eines öffentlichen Stable-Release.

Bis zu diesen Nachweisen ist der technische Produktpfad nicht als gebautes,
vollständig sicheres, für den Pilot freigegebenes oder datenschutzrechtlich
freigegebenes Artefakt zu verstehen.

### Bei Verdacht oder Datenverlust

1. Verlust eines Geräts, unerwartete Passwort- oder Reset-Ereignisse und
   Verdacht auf Manipulation unverzüglich melden.
2. Datenbereiche nicht manuell verschieben, löschen oder mit Fremdwerkzeugen
   bearbeiten, solange ein Backup oder Restore läuft.
