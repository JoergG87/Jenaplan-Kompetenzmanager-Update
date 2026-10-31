# Jenaplan Support-Assistent – Betriebsanleitung

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

Stand: 31. Oktober 2026
Status: unveränderte separate Supportanwendung; kein Bestandteil des normalen
Lehrkraftpakets oder des Build-405-App-Updates. Eine eigene Paketübergabe
benötigt ihre konkreten Paketnachweise.

## Produktgrenze in Build 405

Der Assistent beschreibt die getrennte signierte Reset-Code-Foundation.
Ein von ihm erzeugter Code ist nur eine technische Auth-Recovery-Freigabe.
Die lokale Produkt-App entscheidet weiterhin über dessen Zulässigkeit.

Für eine noch nicht umgestellte Final-V4-Installation kann ein gültiger
Support-Reset ausschließlich bei vollständig verfügbarer ursprünglicher
Installation ausgeführt werden: aktiver Produktroot, aktueller Security
Store, vorhandener zugänglicher installationsgebundener DMK, vollständiges
Final V4, Companion, Schlüsselmetadaten und Managed Documents. Die Produkt-App
prüft diesen Bestand pre-auth read-only und erzeugt und verifiziert ein neues
Safety-`.jkmebackup`, bevor sie Authentifizierungszustand mutiert. Es gibt
keinen ZIP-v1- oder Klartextfallback.

Für V7 besitzt Build 405 keinen passenden Support-Resetadapter. Der Assistent
macht seinen Code dadurch nicht zu einem V7-Reset und darf nicht zum Umgehen
dieser Grenze eingesetzt werden. Die V4→V7- und Restorequalifikation belegt
keine V7-Auth-Recovery über Support Reset.

Recovery-Codes bleiben für V4 und V7 der erste Kontowiederherstellungsweg.
Ein Reset-Code ersetzt weder den geschützten DMK noch Datenbank- oder
Dokumentschlüssel. Fehlt der ursprüngliche DMK oder das ursprüngliche Gerät,
ist dieser Recoveryweg blockiert; er ist keine portable
Backup-Wiederherstellung.

Der Assistent erzeugt ausschließlich den technischen Reset-Code. Er erhält
niemals Passwort, Recovery-Codes, DMK, Database-Key, Schülerdaten, Dokumente
oder Backupinhalt. Final-V4-Preflight, Safety-Backup und Auth-Reset laufen
ausschließlich lokal in der Produkt-App; der Assistent entschlüsselt nichts.
Anfrage und erzeugten Code nur über den vereinbarten geschützten Supportweg
übermitteln, niemals ungeschützt in öffentliche Tickets oder Chats übernehmen.

## Zweck und Grenze

`Jenaplan Support-Assistent.app` ist eine eigenständige Offline-Anwendung für
den Betreiber. Sie erzeugt keinen Zugang und kein Passwort, sondern nur einen
kurz gültigen, unverändert an Installation, Konto, Anfrage, Nonce, Aktion und
Supportschlüssel gebundenen `JKM-SR1`-Reset-Code.

Der Assistent gehört nicht zu `Jenaplan-Kompetenzmanager.app`, Pilot-/Laura-
Paketen oder normalen Updates. Er sucht und öffnet keine fachliche SQLite,
Security Store, Dokumente oder Backups. Private Schlüssel und Passphrase sind
nicht im Bundle oder Supportpaket enthalten.

## Reset-Code erzeugen

1. `Jenaplan Support-Assistent.app` öffnen.
2. `Reset-Anfrage öffnen` wählen und die von der Lehrkraft übermittelte
   `.jkmresetrequest` bewusst auswählen. Es gibt keine automatische Suche.
3. Anwendung, Benutzername-Hinweis, gekürzte Installationskennung,
   Anfragezeit, Ablaufzeit und Status `Gültig` prüfen.
4. Einen menschlichen Installationsnamen wie `Mara Beispiel-Mac` eintragen und den
   lesbaren Anfragecode telefonisch abgleichen. Name und Anfragecode sind nur
   Zuordnungshilfen; die Sicherheit bleibt an die technische UUID gebunden.
5. Prüfen, dass `support-2026-b`, Status `aktiv` und der erwartete gekürzte
   Fingerprint angezeigt werden.
6. Den extern verwahrten verschlüsselten privaten PKCS#8-Schlüssel bewusst
   auswählen und dessen Passphrase eingeben. Der Assistent akzeptiert nur
   Dateirechte `600` und prüft den Schlüssel gegen den gebündelten Public Key.
7. 15, 30, 60 oder 120 Minuten wählen und `Reset-Code erzeugen` auslösen.
8. Den Code nur bewusst kopieren oder als neue `.jkmresettoken`-Datei speichern.
   Vorhandene Dateien werden nicht überschrieben. Es gibt keine automatische
   Übertragung.

Bei ungültiger, beschädigter, noch nicht gültiger oder abgelaufener Anfrage,
falschem Schlüssel, falscher Passphrase oder nicht sicher schreibbarem Audit
bricht der Vorgang ohne Ergebnis ab.

## Technisches Audit

Der Assistent schreibt lokal unter
`~/Library/Application Support/Jenaplan Support-Assistent/audit.jsonl` genau:

- UTC-Zeitpunkt
- Request-ID
- Key-ID
- Aktion `reset_code_created`

Audit enthält niemals Reset-Code, Passwort, Passphrase, privaten Schlüssel,
Nonce, interne Payload, Installationsname, Benutzername, Schülerdaten oder
lokale Quellpfade. Die Datei besitzt Rechte `600`, ihr Ordner `700`.

## Paket und Übergabe

Das separate Paket wird ausschließlich mit
`scripts/build_macos_support_assistant.sh` auf macOS arm64 erzeugt. Es enthält
die Support-App, diese Anleitung, Versionsangaben und Prüfsummen. Es enthält
keine Produkt-App, Datenbank, Dokumente, Backups, Runtime-Daten, Requests,
Tokens, privaten Schlüssel oder Passphrase.

Build 405 ändert weder Assistent, JKM-SR1, Requestdatei, Registry noch
Support-Audit. Vor einer gesonderten Supportpaket-Übergabe sind die konkreten
Paketbytes, Prüfsummen, Signatur, ein Geheimnisscan und eine synthetische
Anfrage zu prüfen. Die Schlüsselverwaltung ist vom normalen App-Update und von
der Sparkle-Updatesignierung getrennt. Dieses Dokument behauptet keine
Developer-ID- oder Apple-Notarisierungsfreigabe des Supportpakets.
