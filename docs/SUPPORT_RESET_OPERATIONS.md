# Jenaplan Support-Reset - interne Betriebsanleitung

Stand: 31. Oktober 2026
Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

## Geltung: V4 ja, V7 nein

Build 405 unterstützt den bestehenden Support-Reset ausschließlich für noch
nicht umgestellte Final-V4-Installationen. Für V7 gibt es keinen passenden
Support-Resetadapter. Eine sichtbare allgemeine Wiederherstellungsoberfläche
ist keine V7-Resetfreigabe. Die V4-spezifische Prüfung darf nicht umgangen und
keine Datenbank für einen Reset zurückgestuft werden.

Recovery-Codes sind bei V4 und V7 der erste vorgesehene
Kontowiederherstellungsweg. Ein Support-Reset ersetzt weder den vorhandenen
Data Master Key (DMK) noch einen Database-Key. Er entschlüsselt keine
Schülerdaten für den Support und bietet keinen allgemeinen Gerätewechselweg.

## Voraussetzungen für eine V4-Auth-Recovery

Der aktive ursprüngliche Produktroot, Security Store, vorhandene zugängliche
Keychain-DMK, Schlüsselmetadaten, vollständige Final-V4-Hauptdatenbank,
Dokument-Companion und registrierte Managed Documents müssen vorhanden und
vollständig prüfbar sein. Die App muss die Anfrage und den signierten
`JKM-SR1`-Reset-Code an dasselbe Konto, dieselbe Installation, Anfrage und
Einmalbindung binden können. Gültigkeitszeit und aktiver Supportschlüssel
müssen passen.

Die lokale Produkt-App lädt den DMK nur existing-only, ohne Ersatzschlüssel
anzulegen. Sie prüft den V4-Bestand vor dem Auth-Reset read-only und erzeugt
sowie verifiziert ein neues vollständiges verschlüsseltes
Safety-`.jkmebackup`. Erst danach ist der atomare Security-Commit zulässig.
Historische `.jkmbackup`-/ZIP-v1- oder Klartextpfade sind kein Fallback.

<!-- pagebreak -->

## Betreuter Ablauf

1. Zuerst klären, ob `Recovery-Code verwenden` im Anmeldedialog möglich ist.
   Den Code gibt die Lehrkraft ausschließlich lokal in die App ein.
2. App-Version und tatsächlichen Datenstand prüfen. Bei V7 oder unklarem
   Schema keinen Support-Reset durchführen; die Pilotbetreuung klärt das
   weitere Vorgehen ohne Resetversprechen.
3. Bei zulässigem V4 `Weitere Wiederherstellungsmöglichkeiten` öffnen und
   `Reset-Anfrage erstellen` wählen. Die technische Anfrage nur über einen
   vereinbarten geschützten Weg an die zuständige Betreuung übergeben.
4. Im getrennten Offline-Support-Assistenten Anfrage und Identität prüfen und
   einen kurz gültigen signierten Code für genau diese Anfrage erzeugen.
   Das Verfahren steht in der bestehenden Support-Assistent-Anleitung.
5. Den Code ausschließlich geschützt an die Lehrkraft zurückgeben. In der
   Produkt-App `Reset-Code eingeben` wählen, den Code prüfen lassen und die
   angezeigte Vorschau kontrollieren.
6. Nur nach bewusster Bestätigung den lokalen Vorgang einschließlich
   vollständiger Prüfung und Safety-Backup ausführen lassen. Weder App noch
   Mac währenddessen gewaltsam beenden.
7. Nach Abschluss den vorgesehenen Neustart und die neue Passwortanlage
   durchführen, neue Recovery-Codes getrennt sichern und die Anmeldung
   kontrollieren. Frühere Gerätecredentials werden durch den Auth-Reset
   unwirksam. Vorhandene Fachdaten und Datenschlüssel bleiben bestehen.

Anfrage, Reset-Code und Audit sind keine Freigabe zum Zugriff auf
Datenbankinhalte. Passwörter, Recovery-Codes, DMK, Database-Key, Backups oder
Schülerdokumente gehören nicht an den Support-Assistenten.

## Sichere Abbruchgrenzen

Bei ungültiger/abgelaufener Anfrage oder ungültigem Token keine Änderungen am
Bestand vornehmen. Eine neue Anfrage nur über den normalen Appablauf und nach
Klärung des Fehlers erzeugen.

Bei nicht zugänglichem Schlüsselbund, fehlendem DMK, beschädigtem oder
unvollständigem V4-Bestand, fremden Restore-/Upgradebelegen oder fehlgeschlagenem
Pflichtbackup abbrechen. Bei einem solchen Preflight-/Backupfehler erfolgt
kein Auth-Reset; Passwort, Recoveryzustand, Security-Epoch und
Gerätecredentials werden nicht durch den Reset ersetzt. Nach einem unklaren
Commitzustand dagegen keinen unveränderten Authzustand behaupten: Die App
hält sicher an, vorhandene Belege müssen erhalten bleiben und der Support muss
den Zustand prüfen.

Keine Schlüsselbundeinträge, WAL-/SHM-/Journaldateien, Quellbackups oder
Abschlussbelege löschen. Keine einzelne Datenbankdatei zurückkopieren, keine
leere Ersatzinstallation anlegen und keine alte App auf V7 starten. Ein
Support-Reset ist kein Reparaturpfad für Datenbank, Schema oder Upgrade.

Bei fehlendem ursprünglichem Gerät oder verlorenem DMK gibt es in Build 405
keinen Mastercode und keine portable Entschlüsselungs-Recovery. Ein
vorhandenes `.jkmebackup` allein hebt diese Grenze nicht auf.

## Nachweise und getrennte Paketfreigabe

Der Build-405-Produktcode enthält den beschriebenen V4-Vertrag und verweigert
die V7-Umgehung. Die technische Produktqualifikation von V4→V7,
Schlüsselbundkontinuität, Anmeldung, Backup/Restore und 404-Ablehnung ist kein
Nachweis eines neuen V7-Support-Resets.

Der separate Offline-Assistent, seine `JKM-SR1`-Foundation,
Public-Key-Registry und Auditfunktion bleiben unverändert. Er ist kein
Bestandteil des normalen Lehrkraftpakets. Vor seiner eigenen Übergabe sind
sein konkretes Paket, Prüfsummen, Signatur, externe private Schlüsselverwaltung
und eine synthetische Anfrage zu prüfen. Hier wird weder ein Neubau noch eine
Developer-ID-/Notarisierungsfreigabe dieses Supportpakets behauptet.

## Datensparsame Supportübergabe

Für die erste Klärung reichen App-Version/Build, Betriebssystem,
Arbeitsschritt, Zeitpunkt und die angezeigte technische Kennung. Screenshots
vorher von Namen und Inhalten bereinigen. Keine vollständigen personenbezogenen
Daten, Schlüssel, Passwörter, Recovery- oder Reset-Codes ungeschützt versenden.
Eine gegebenenfalls notwendige gesonderte Datenübergabe verlangt den dafür
schulisch freigegebenen geschützten Prozess.
