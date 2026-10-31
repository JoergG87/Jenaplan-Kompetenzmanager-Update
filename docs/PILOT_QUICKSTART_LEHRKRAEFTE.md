# Schnellstart für Lehrkräfte

Version {{PILOT_VERSION}} / Build {{PILOT_BUILD}}

> [!HINWEIS]
> Mac-Pilotversion {{PILOT_VERSION}} / Build {{PILOT_BUILD}}.

1. Bei einem Update zuerst in Build 404 ein vollständiges verschlüsseltes
   Backup erstellen und prüfen. App vollständig beenden, DMG öffnen, App
   nach `Programme` ziehen und von dort starten.
2. Bei frischer Installation ein App-Passwort festlegen und die zehn
   Recovery-Codes getrennt vom Mac sichern. Beim Update das bisherige
   Passwort verwenden.
3. Anmelden. Schuljahr `2026/27`, Entwicklungsbuch und 331 Kompetenzen sind
   bereits vorhanden.
4. Unter `Stammdaten` mindestens eine Stammgruppe und einen Kurs anlegen;
   Kursverbünde sind optional.
5. Schüler anlegen.
6. `Schüler` öffnen, das Kind über `Profil öffnen` auswählen und unter
   `Überblick` die Karte `Fächer für die Dokumentation` mit `Aufklappen` öffnen.
   `Für dieses Kind individuell festlegen` wählen, Unterrichtsfächer markieren
   und `Speichern` wählen.
7. V7 durch die Pilotbetreuung bewusst aktivieren lassen. Danach bei Bedarf
   unter `Einstellungen > Unterrichtszeiten` Zeitvorlagen und unter
   `Stundenplan` Stunden sowie A-/B-Wochen einrichten. Der Stundenplan ist
   keine Startvoraussetzung.
8. Eine Beobachtung erfassen und bewusst speichern.
9. Kompetenz-Cockpit, Bericht oder LEG bei Bedarf öffnen. Bericht:
   `Auswählen -> Schreiben -> Prüfen & finalisieren`; LEG: `Vorbereitung -> Im
   Gespräch -> Vereinbarungen & Abschluss`.
10. Unter `Einstellungen > Datensicherung` mit `Backup erstellen` eine
    verschlüsselte `.jkmebackup` anlegen und mit `Backup prüfen …` prüfen.

## V7 und Updategrenze

Das App-Update allein migriert keine Daten; eine frische Installation startet
ebenfalls in V4. Erst die betreute Wartung aktiviert V7 mit vollständigem
geprüftem Quellbackup und kontrolliertem Neustart. Mit dem bisherigen
Passwort anmelden und die Daten prüfen. Bei einem Fehler Bestand und
Quellbackup erhalten und die Betreuung hinzuziehen.

Build 404 kann V7 nicht öffnen. Eine Rückkehr erfordert ein geeignetes
vollständiges V4-Backup im ursprünglichen Schlüsselkontext und kann spätere
Änderungen verlieren. Keine Einzeldateien zurückkopieren.

Der A-/B-Rhythmus läuft auch in Ferien nach Kalenderwochen weiter.
Eine Einzelwochenkorrektur verschiebt den Grundrhythmus nicht. Bei einer
kombinierten Stunde muss eine Beobachtung einem konkreten Fach zugeordnet
werden; sie bewertet nicht automatisch beide Fächer.

## Fachauswahl beim Kind

Auswählbar sind EPU, Deutsch, Mathematik, Kreatives Gestalten, Sport, Ethik,
Religion, Musik, Englisch und Schulgarten. Selbst- und Sozialkompetenz sowie
Arbeits-/Lernkompetenz gehören zur immer verfügbaren `Überfachlichen
Entwicklung` und werden nicht als Unterrichtsfächer ausgewählt.

Die Auswahl priorisiert den normalen Dokumentationsworkflow; sie löscht keine
Fächer, Kompetenzen oder Beobachtungen und ist keine Berechtigungsgrenze. Im
Beobachtungsdialog stehen die ausgewählten Unterrichtsfächer unter `Fächer`,
andere aktive Unterrichtsfächer unter `Weitere Fächer`. Eine leere individuelle
Auswahl bleibt leer und erzeugt keine automatische neue Auswahl.

## Wichtige Grenzen

> [!SICHERHEIT]
> - Die App arbeitet lokal, ohne Cloud und ohne KI-Verarbeitung von Fachdaten.
> - Finale Bericht- und LEG-PDFs liegen verschlüsselt im verwalteten
>   Produktbereich und öffnen read-only im sicheren In-App-Viewer.
> - Der Viewer unterstützt mehrseitiges Scrollen, Zoom sowie Schließen und
>   erneutes Öffnen; Export, Drucken oder Teilen werden nicht versprochen.
> - `.jkmebackup` ist installationsgebunden und kein allgemeiner
>   Gerätewechselweg.
> - Recovery-Codes sind der normale erste Wiederherstellungsweg. Support Reset
>   ist nur für einen intakten Final-V4-Bestand vor der V7-Umstellung ein
>   betreuter Ausnahmeweg. Für V7 ist kein entsprechender Adapter vorhanden.
>   Kein Recovery-Verfahren ersetzt einen verlorenen lokalen Schlüssel.
> - Keine Passwörter, Schlüssel, Recovery-Codes oder personenbezogenen Daten
>   ungeschützt an den Support senden.

Weitere Einzelheiten stehen im Benutzerhandbuch und in der Unterlage
„Sicherheit und Verschlüsselung“.
