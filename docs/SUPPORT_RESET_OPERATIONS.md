# Jenaplan Support-Reset – aktuelle interne Betriebsgrenze

## Status für den geplanten Pilotstand 0.4.0 / Build 400

Support Reset ist im Final-V4-Cipher-Produktpfad kontrolliert blockiert. Die
App komponiert für diesen Ablauf keine Pre-Auth-Backup-Factory und zeigt
stattdessen verständlich, dass die weitere Wiederherstellung in dieser
App-Version nicht verfügbar ist.

Der Grund ist eine feste Sicherheitsgrenze: Vor einem Passwortreset müsste
ohne bereits entsperrten Fachbestand ein verpflichtendes, vollständiges und
erneut verifiziertes Cipher-Sicherheitsbackup erstellt werden. Diese
Komposition ist noch nicht separat freigegeben. Der frühere ZIP-v1-
Backupvertrag und Klartextpfade sind im Cipher-Produktmodus keine aktive
Ausweichlösung.

## Zulässiger Supportablauf

1. Zuerst vorhandene Recovery-Codes als vorgesehenen Wiederherstellungsweg
   verwenden.
2. Keine Final-V4-, Companion-, Dokument- oder Schlüsseldateien manuell
   verschieben, ersetzen oder mit SQLite-Werkzeugen öffnen.
3. Keinen alten `.jkmbackup`-, ZIP-v1- oder Klartextbestand einspielen.
4. Keine Support-Reset-Anfrage als Zusage interpretieren, dass ein Reset im
   aktuellen Produktpfad abgeschlossen werden kann.
5. Bei Verlust aller Recovery-Codes und des Passworts den Fall eskalieren und
   den verschlüsselten Bestand unverändert sichern. Es gibt derzeit keinen
   freigegebenen Umgehungs- oder Mastercode.

Ein Passwort, Recovery-Code oder signierter Reset-Code ist nicht der DMK und
nicht der Datenbankschlüssel. Der installationsgebundene `.jkmebackup`-
Restore benötigt weiterhin den passenden bestehenden DMK der Installation.

## Getrennte historische Foundation

Die vorhandenen `JKM-SR1`-Anfrage-, Token-, Public-Key-Registry- und
Support-Assistent-Komponenten bleiben als historische beziehungsweise
technische Foundation dokumentiert. Der separate Offline-Assistent erzeugt
keinen Benutzerzugang, kein Passwort und keine Entschlüsselung und liest keine
Fachdaten. Diese Foundation ist jedoch nicht gleichbedeutend mit einem aktiven
Support-Reset im Final-V4-Produktpfad.

## Voraussetzungen für eine spätere Aktivierung

Eine spätere Freigabe benötigt mindestens:

- eine separat entschiedene sichere Cipher-Pflichtbackup-Komposition an der
  Pre-Auth-Grenze;
- vollständige Prüfung von DMK-, Database-Key-, Envelope-, Companion- und
  Managed-Document-Verträgen;
- Wiederanlauf-, Abbruch-, Rollback- und Datenverlusttests;
- reale macOS-/Keychain-Abnahme;
- Paket-, Schlüssel-, Signatur- und Geheimnisscan;
- ausdrückliche Product-Owner-, Security-, Pilot- und Releasefreigabe.

Bis dahin darf kein Supportpaket als produktiv nutzbarer Pilot-Recoveryweg
übergeben werden.
