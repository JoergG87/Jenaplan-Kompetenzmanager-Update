# Jenaplan Support-Reset – aktuelle interne Betriebsgrenze

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

> [!HINWEIS]
> Inhaltlich finaler Reviewstand vor der Versionsanhebung; noch kein finales
> Pilot- oder Releaseartefakt.

Support Reset ist im Final-V4-Cipher-Produktpfad ausschließlich als
installationsgebundene Auth-Recovery aktiv. Die App prüft zuerst den
vollständigen JKM-SR1-Vertrag, lädt dann über eine private existing-only Grenze
den vorhandenen DMK ohne Lifecycle-Mutation, öffnet Final V4, Companion und
Managed Documents pre-auth read-only und erzeugt und verifiziert ein neues
`.jkmebackup`. Erst danach darf der bestehende atomare Security-Commit laufen.
Der frühere ZIP-v1-Backupvertrag und Klartextpfade sind im Cipher-Produktmodus
keine Ausweichlösung.

## Zulässiger Supportablauf

1. Zuerst vorhandene Recovery-Codes als vorgesehenen Wiederherstellungsweg
   verwenden.
2. Keine Final-V4-, Companion-, Dokument- oder Schlüsseldateien manuell
   verschieben, ersetzen oder mit SQLite-Werkzeugen öffnen.
3. Keinen alten `.jkmbackup`-, ZIP-v1- oder Klartextbestand einspielen.
4. Support Reset nur durchführen, wenn der ursprüngliche aktive Produktroot,
   Security Store, Keychain-DMK, Schlüsselmetadaten, Final V4, Companion und
   Managed Documents vollständig verfügbar sind.
5. Bei Preflight- oder Backupfehler abbrechen. Passwort, Recovery-Codes, Epoch
   und Gerätecredentials bleiben dann unverändert; der Fehler ist kein Auftrag
   zur Reparatur oder Neuerzeugung.
6. Bei verlorenem Mac oder fehlendem/unzugänglichem DMK den verschlüsselten
   Bestand unverändert sichern und eskalieren. Es gibt keinen Umgehungs- oder
   Mastercode und keine portable Recovery.

Ein Passwort, Recovery-Code oder signierter Reset-Code ist nicht der DMK und
nicht der Datenbankschlüssel. Der installationsgebundene `.jkmebackup`-
Restore benötigt weiterhin den passenden bestehenden DMK der Installation.

## Getrennte Support-Foundation

Die vorhandenen `JKM-SR1`-Anfrage-, Token-, Public-Key-Registry- und
Support-Assistent-Komponenten bleiben als unveränderte technische Foundation
dokumentiert. Der separate Offline-Assistent erzeugt
keinen Benutzerzugang, kein Passwort und keine Entschlüsselung und liest keine
Fachdaten. Er erhält weder DMK, Database-Key, Backup noch Dokumente; die
Final-V4-Prüfung und das Pflichtbackup bleiben ausschließlich lokal in der
Produkt-App.

## Offene reale Betriebsabnahme

Vor Pilotübergabe bleiben die reale macOS-Keychain-/Code-Signing-Abnahme, der
Support-Assistent-Paket-/Schlüssel-/Signatur-/Geheimnisscan, Developer ID,
Notarisierung und die ausdrückliche Pilot-/Releasefreigabe offen. Diese offenen
Gates ändern weder JKM-SR1 noch den lokal implementierten Sourcevertrag und
begründen keine Geräteportabilität.
