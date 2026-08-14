# Jenaplan Support-Assistent – Betriebsanleitung

## Produktstatus 0.4.0 / Build 400

Der Support-Assistent beschreibt die getrennte signierte Reset-Code-
Foundation. Im aktuellen Final-V4-Cipher-Produktpfad kann ein gültiger
Support-Reset ausschließlich auf der ursprünglichen intakten lokalen
Installation ausgeführt werden: aktiver Produktroot, aktueller Security Store,
vorhandener zugänglicher installationsgebundener DMK, vollständiges Final V4,
Companion, Schlüsselmetadaten und Managed Documents. Die Produkt-App prüft
diesen Bestand pre-auth read-only und erzeugt und verifiziert ein neues
`.jkmebackup`, bevor sie Authentifizierungszustand mutiert. Es gibt keinen
ZIP-v1- oder Klartextfallback.

Recovery-Codes bleiben der erste vorgesehene Kontowiederherstellungsweg. Ein
Reset-Code würde weder den geschützten DMK noch Datenbank- oder
Dokumentschlüssel ersetzen. Fehlt der ursprüngliche DMK oder das ursprüngliche
Gerät, ist dieser Recoveryweg blockiert; er ist keine portable
Backup-Wiederherstellung.

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

Der Final-V4-Produktpfad ändert weder Assistent, JKM-SR1 noch Requestdatei,
Registry oder Support-Audit. Vor Pilotübergabe bleiben Paket, Prüfsummen,
synthetische Anfrage, reale Keychain-/Code-Signing-Grenze,
Developer-ID-Signierung und Notarisierung separat zu prüfen.
