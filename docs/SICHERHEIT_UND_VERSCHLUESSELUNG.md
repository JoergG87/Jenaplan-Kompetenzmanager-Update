# Sicherheit und Verschlüsselung

Stand: 1. November 2026
Geltung: Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}, macOS arm64

Dieses Dokument erklärt die Sicherheitsfunktionen des Build-406-Produktcodes.
Die Veröffentlichung von 0.5.1/406 benötigt eine gesonderte Freigabe des finalen
Artefaktstands. Die technische Qualifikation ersetzt keine schulische
Datenschutz- oder Betriebsfreigabe.

## 1. Lokal arbeiten und den Mac schützen

Der Jenaplan-Kompetenzmanager speichert Fachdaten lokal, getrennt vom
App-Bundle. Er synchronisiert keine Schülerdaten mit einer Cloud und bindet
keine KI-Dienste ein. Die Prüfung auf App-Updates ist davon getrennt: Sie
verwendet den bestehenden Pilotkanal und benötigt eine Netzwerkverbindung.

Schülerdaten, Beobachtungen, Dokumente, Berichte und Lernentwicklungsgespräche
sind schutzbedürftig. Verwenden Sie ein schulisch freigegebenes Gerät, ein
persönliches macOS-Benutzerkonto und die Gerätesperre. FileVault und weitere
Schutzmaßnahmen richten sich nach den Vorgaben der Schule. Die App ersetzt
diese Maßnahmen nicht.

## 2. Passwort, App-Sperre und Recovery-Codes

Das lokale App-Passwort schützt den Zugang. Bei der ersten Einrichtung werden
Passwortbestätigung und das gesonderte Sichern der Recovery-Codes verlangt.
Passwortwechsel und eine Wiederherstellung mit Recovery-Code sind in der App
vorhanden. Fehlversuche können eine zeitweilige Sperre auslösen; warten Sie die
angezeigte Zeit ab.

Optional stehen eine Geräteanmeldung über den macOS-Schlüsselbund und Touch ID
zur Verfügung. Die App zeigt an, wenn Touch ID nicht eingerichtet, nicht
verfügbar oder vorübergehend gesperrt ist. Die Passwortanmeldung bleibt die
Alternative; sie kann einen fehlenden Datenschlüssel nicht ersetzen.

Die App sperrt nach der eingestellten Inaktivitätszeit oder nach Ruhezustand.
Mit `Jetzt sperren` ist eine sofortige Sperre möglich. Auch bei einer
Geräteanmeldung bleibt diese Sperre bestehen. Die App-Sperre und die
Datenverschlüsselung erfüllen unterschiedliche Aufgaben.

> [!SICHERHEIT]
> Recovery-Codes sind ein Wiederherstellungsweg für das lokale Konto, keine
> Datenbankschlüssel. Ein verwendeter Code wird verbraucht. Bewahren Sie die
> Codes getrennt vom Mac an einem geschützten Ort auf und geben Sie sie nicht
> an den Support weiter. Bei Verlust des App-Passworts zuerst
> `Recovery-Code verwenden` im Anmeldedialog wählen.

## 3. Verschlüsselte Daten und Dokumente

Die fachliche Hauptdatenbank und der Dokument-Companion werden mit SQLCipher
verschlüsselt geöffnet. Der verbindliche macOS-Provider ist das Python-Binding
`sqlcipher3` in Version `0.6.2+jkm.sqlcipher4170.1` mit SQLCipher
`4.17.0 community`, SQLite `3.53.3` und CommonCrypto. Eine fehlende oder andere
Engine sowie Standard-SQLite sind im Produktpfad kein Ersatz; der Start hält an.

Build 406 kann eine vollständige, noch nicht umgestellte Final-V4-Installation
und eine vollständig umgestellte V7-Installation öffnen. Final V4 und V7
haben getrennte exakte Schemaidentitäten. V7 wird ausschließlich
über den bewusst bestätigten Migrationsassistenten aktiviert. Ein normaler
App-Start erkennt Final V4 und bietet die Umstellung an, migriert aber nicht ohne Zustimmung. Unbekannte oder unvollständige Schemata werden nicht still übernommen.
Es gibt keine automatische Übernahme alter Klartext-, V3- oder Testdaten.

Anhänge, allgemeine Schülerdokumente und finale Bericht-/LEG-PDFs liegen als
verschlüsselte Managed Documents vor. Der Companion registriert die
Dokumentgenerationen; beim Lesen werden Inhalt und Zuordnungen geprüft.
Finale Bericht- und LEG-PDFs öffnen im schreibgeschützten In-App-Viewer mit
mehrseitiger Anzeige, Scrollen und Zoom. Dieser finale Artefaktpfad bietet keine
OS-Öffnung, Export-, Druck- oder Teilenfunktion.

Der gesonderte Kompetenzübersicht-Export für Eltern ist eine andere,
ausdrücklich angebotene Funktion. Ein bewusst exportiertes PDF liegt außerhalb
des verschlüsselten Managed-Document-Speichers. Schützen Sie die Ausgabedatei
und ihren Übertragungsweg nach Schulvorgabe. Ebenso bleiben ursprünglich
importierte Dateien an ihrem bisherigen Speicherort außerhalb des App-Schutzes.

## 4. Schlüsselbund und Datenschlüssel

Das App-Passwort ist nicht der Datenbankschlüssel. Ein davon getrennter Data
Master Key (DMK) wird im macOS-Schlüsselbund geschützt. Ein zufälliger
Database-Key wird in einer mit dem DMK geschützten Schlüsselhülle aufbewahrt
und öffnet Haupt- und Companion-Datenbank. Dokumente besitzen eigene zufällige
Schlüssel; Backups verwenden eine getrennte Schlüsseldomäne.

Passwortwechsel, Auth-Recovery und der für V4 zulässige Support-Reset erzeugen
keinen neuen DMK. Bei der V4→V7-Umstellung bleiben vorhandenes Konto,
App-Passwort und ursprünglicher Schlüsselkontext bestehen. Die vorhandenen
Datenschlüssel werden nicht rotiert.

> [!WARNUNG]
> Bei einer bestehenden Installation führt ein fehlender oder nicht
> zugänglicher Schlüssel zum sicheren Halt. Die App legt dafür keinen
> Ersatzschlüssel und keinen leeren Ersatzbestand an. Ein korrektes Passwort,
> ein Recovery-Code oder ein Support-Reset-Code kann einen verlorenen DMK
> nicht wiederherstellen.

Wenn macOS nach Zugriff auf den Schlüsselbund fragt, prüfen Sie die anfragende
App und geben Sie ausschließlich die bewusst installierte Anwendung frei.
Entsperren Sie einen gesperrten eigenen Schlüsselbund über den vorgesehenen
macOS-Weg. Bleibt der Zugriff verweigert, wenden Sie sich an die Betreuung.
Löschen Sie keine Schlüsselbundeinträge und ändern Sie keine globalen
Sicherheits- oder Zugriffsrechte als Reparaturversuch.

## 5. Kontrollierter Start und Fehlerverhalten

Vor einer normalen Sitzung prüft die App den vorhandenen Installationsbestand,
Zustandsbelege und erforderliche Schlüssel. Nach Anmeldung folgen die exakte
Schema-, Integritäts- und Dokumentprüfung. Bei V7 wird zusätzlich der
installationsgebundene authentisierte Abschlussbeleg der Migration geprüft.
Ein isoliert kopierter Main-Datenbankstand genügt nicht.

Fehlende Dateien, beschädigte Daten, widersprüchliche Zuordnungen, unvollständige
Upgrades sowie unbekannte oder unzulässige Begleitdateien können den Start
blockieren. Die Meldung ist eine Schutzentscheidung und keine Aufforderung,
Dateien zu entfernen. Manche kontrollierten Restorezustände können über den
vorhandenen Recoveryablauf wieder geprüft werden; eine automatische Reparatur
beliebiger beschädigter Bestände ist nicht implementiert.

Bei einem Starthalt Meldung und technische Kennung ohne personenbezogene
Inhalte festhalten, die App schließen und die Betreuung hinzuziehen. Keine
Datenbank mit Fremdwerkzeugen öffnen, keine WAL-/SHM-/Journaldateien löschen,
keine Einzeldateien austauschen und keine Neuinitialisierung erzwingen.

## 6. Backup und Wiederherstellung

Unter `Einstellungen > Datensicherung` erstellt die App ausschließlich
verschlüsselte und authentisierte `.jkmebackup`-Dateien. Das Vollbackup enthält
Hauptdatenbank, Companion, registrierte verschlüsselte Dokumentgenerationen
sowie notwendige Keyset- und Schlüsselhüllen-Metadaten. App-Passwort,
Recovery-Codes, Touch-ID-/Gerätecredentials und DMK sind nicht enthalten.

V4 und V7 haben unterschiedliche exakte Schema- und Restoreverträge. Die
laufende Installation sichert ihren jeweiligen zugelassenen Stand. Eine
vorhandene Sicherung lässt sich mit `Backup prüfen …` unabhängig vom
Erstellungslauf vollständig prüfen. Diese Prüfung verändert den aktiven
Fachbestand nicht.

Restore verlangt Prüfung, Vorschau und bewusste Bestätigung. Der vorbereitete
Bestand wird vollständig geprüft, ein verschlüsseltes Sicherheitsbackup des
aktuellen Bestands erstellt und ein separater Worker übernimmt den Austausch
nach vollständiger App-Beendigung. Anschließend folgen kontrollierter Neustart,
Prüfung und erneute Anmeldung. Bei Fehlern nutzt die App ihren vorhandenen
Rollback-/Recoveryvertrag oder hält mit erhaltenen Belegen an; dies ist keine
allgemeine Verlustfreiheitsgarantie.

> [!WARNUNG]
> `.jkmebackup` bleibt an die ursprüngliche geschützte Installation und den
> passenden vorhandenen Schlüsselkontext gebunden. Es ist kein allgemeiner
> Gerätewechselweg und ersetzt keine DMK-Recovery. Ein verlorener Mac oder
> Schlüssel ist durch eine Backupdatei allein nicht abgesichert.

Die Schrittfolge und Fehlerfälle stehen in `Backup und Wiederherstellung`.
Keine historischen `.jkmbackup`-/ZIP-v1- oder Klartextwerkzeuge auf den
verschlüsselten Produktbestand anwenden.

## 7. Update von 404 oder 405 auf 406 und Rückkehrgrenze

Vor dem Update ein vollständiges verschlüsseltes `.jkmebackup` erstellen und prüfen.

Nach dem Update über den bestehenden Pilotkanal erkennt Build 406 einen vorhandenen Final-V4-Bestand automatisch. Melden Sie sich mit Ihrem bisherigen Passwort an. Der Dialog `Datenbestand aktualisieren` erklärt Sicherung, Umstellung und Rückkehrgrenze. Lesen Sie die Hinweise, setzen Sie `Ich möchte die Aktualisierung jetzt starten.` und wählen Sie `Aktualisierung starten`. Mit `Später` verschieben Sie die Umstellung; es wird nichts migriert.

Die App erstellt eine vollständige verschlüsselte V4-Sicherung und prüft sie unabhängig. Erst danach folgt die kontrollierte Umstellung nach V7. Lassen Sie den Mac eingeschaltet und starten Sie keine zweite App. Die Anzeige nennt die tatsächlichen Phasen; es gibt keine Prozentprognose. Nach vollständiger Zielprüfung startet die App regulär neu. Melden Sie sich mit dem bisherigen Passwort an und prüfen Sie Ihre Daten. Bereits vollständig aktualisierte V7-Bestände werden nicht erneut migriert.

Bei einem Fehler bleiben Bestand, Sicherungen und Wartungsbelege erhalten. Notieren Sie Version/Build, Zeitpunkt, Handlung und den personenfreien Supporthinweis. Wenden Sie sich an die Pilotbetreuung; senden Sie keine Passwörter, Recovery-Codes, Schlüssel oder Schülerdaten ungeschützt. Nur wenn die App `Abschluss prüfen` anbietet, kann dieser bewusst bestätigt werden. Keine Dateien löschen, keinen neuen Bestand anlegen und keine alte App als Reparatur starten. Terminalbefehle sind für Lehrkräfte nicht erforderlich.

Eine Neuinstallation legt zunächst einen leeren verschlüsselten Final-V4-Bestand an. Nach abgeschlossener Einrichtung wird der Assistent beim folgenden Programmstart angeboten. Es gibt keine direkte V7-Erstanlage.

> [!WARNUNG]
> Build 404 kann eine V7-Datenbank nicht öffnen. Eine Rückkehr zu V4 verlangt
> eine geeignete vollständige V4-Sicherung und einen betreuten vollständigen
> Rückfall im ursprünglichen Schlüsselkontext. Die Installation von 404 allein
> ist kein Downgrade. Änderungen seit dem V4-Sicherungszeitpunkt können bei
> einer Rückkehr zu diesem Backup verloren gehen.

Ein V4-Backup nicht direkt in eine aktive V7-Installation einspielen. Der
Build-406-Produktpfad bietet keinen allgemeinen Rückmigrationsassistenten.

## 8. Grenzen des Support-Resets

Recovery-Codes sind für V4 und V7 der erste Kontowiederherstellungsweg. Für
eine noch nicht umgestellte V4-Installation existiert ein betreuter
Support-Reset ausschließlich bei intaktem ursprünglichem Bestand, zugänglichem
DMK, vollständiger lokaler V4-Prüfung und erfolgreich erzeugtem und verifiziertem
Safety-`.jkmebackup`. Er setzt nur Anmelde- und Recoveryzustände zurück und
gibt dem Support keinen Zugriff auf Schülerdaten.

Für V7 ist dieser V4-spezifische Support-Reset nicht verfügbar. Auch wenn eine
allgemeine Wiederherstellungsoberfläche sichtbar ist, ergibt sich daraus kein
V7-Resetweg. Ohne nutzbaren Recovery-Code ist die Pilotbetreuung erforderlich;
ein Mastercode, ein Schlüsselersatz und eine Datenentschlüsselung durch den
Support sind nicht implementiert.

## 9. Löschen und Aufbewahren

Das Entfernen einer Beobachtung ist ein Soft Delete: Die Beobachtung wird aus
aktiven Ansichten genommen, historische Rating-Zuordnungen bleiben erhalten.
Auch das Entfernen eines verwalteten Dokuments bedeutet keine garantierte
physische Löschung seiner Datei. Frühere Dokumentgenerationen, verschlüsselte
Backups und Restore-/Upgradebelege können weiterhin vorhanden sein.

Build 406 bietet keine automatische schulrechtliche Aufbewahrungsfrist und
keine garantierte sichere SSD-Löschung. Die App automatisch zu deinstallieren
oder nur das App-Bundle zu löschen beseitigt den getrennten Datenbereich und
vorhandene Backups nicht. Die Schule legt Aufbewahrung und eine betreute
vollständige Datenentsorgung fest. Nicht eigenständig technische Belege oder
Dateien zur vermeintlichen Bereinigung entfernen.

## 10. Nachweise, Einschränkungen und zukünftige Möglichkeiten

Die Funktionen entsprechen Build 406. Am Paketquellstand `ddaee98` wurden mit ausschließlich synthetischen Installationen native 404→406 und 405→406, V7-Neustart, Datenerhaltung, vorhandene Schlüssel und Passwörter sowie vollständiges Backup/Restore mit Worker geprüft. Die native Bedienung wurde vom PO bestätigt und unabhängig technisch verifiziert. Diese Nachweise ersetzen keine Paketprüfung geänderter Bytes.

Die Paketstrategie ist weiterhin Ad-hoc-Signierung. Daraus folgen keine
Developer-ID-, Apple-Notarisierungs-, Hardware- oder Sicherheitszertifikate.
Der Pilotkanal besteht; die Veröffentlichung von 406 und die öffentliche
Rückprüfung der ausgelieferten Artefakte sind gesonderte Schritte. Eine
Stable-Freigabe liegt damit nicht vor.

Nicht implementiert oder nicht allgemein nachgewiesen sind portable
Backup-Recovery, Ersatz eines verlorenen DMK, automatische Rückmigration,
Windows-/DPAPI-Produktbetrieb und allgemeine Wiederherstellung nach beliebigen
Abbrüchen oder Stromausfällen. Eine mögliche spätere Erweiterung ist keine
heute verfügbare Funktion.

Die Verschlüsselung verbessert den Schutz kopierter Datendateien. Sie bietet
keinen vollständigen Schutz gegen Malware im angemeldeten macOS-Konto,
Keylogger, Screenshots, Speicheranalyse oder hochprivilegierte Angreifer.
Verlust eines Geräts oder Verdacht auf Datenabfluss unverzüglich nach dem
schulischen Meldeweg melden. Keine Passwörter, Schlüssel, Recovery-Codes,
Reset-Codes oder vollständigen personenbezogenen Daten ungeschützt an den
Support senden.
