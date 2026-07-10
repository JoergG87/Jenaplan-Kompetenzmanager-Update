# Stufenzuordnung fuer Lehrplan-Kompetenzen

Diese Datei dokumentiert die fachliche Stufenlogik fuer den spaeteren Kompetenzkatalog. Sie fuehrt keine technische Speicherung ein und aendert keine bestehenden Kompetenz-IDs.

## Fachliche Stufenwerte

Verbindliche Stufenwerte:

- `Klassenstufe 1-3`
- `Klassenstufe 4`
- `stufenuebergreifend`

`Klassenstufe 1-3` gilt fuer Kompetenzen der Schuleingangsphase oder frueheren Grundschuljahre, sofern der Lehrplan keine klare Klasse-4-Progression daraus macht.

`Klassenstufe 4` gilt fuer fachlich erweiterte, verbindliche oder klar hoehere Anforderungen der Klassenstufe 4.

`stufenuebergreifend` gilt, wenn eine eindeutige Trennung fachlich nicht moeglich oder nicht sinnvoll ist.

## Filterprinzip

Die spaetere UI filtert Kompetenzen, sperrt sie aber nie.

Standardansicht:

- `Passende Kompetenzen`
- unterscheidbare Filter fuer `Klassenstufe 1-3` und `Klassenstufe 4`

Zusaetzlich:

- `Alle Kompetenzen anzeigen`

Klasse-4-Kompetenzen bleiben auch fuer juengere Kinder auswaehlbar. Das unterstuetzt jahrgangsgemischte Gruppen und individuelle Lernwege.

## Stufenuebergreifende Kompetenzen

Stufenuebergreifende Kompetenzen werden genutzt, wenn:

- der fachliche Kern ueber mehrere Stufen gleich bleibt,
- der Lehrplan keine saubere Trennung ermoeglicht,
- eine Trennung nur technische Abhakpunkte erzeugen wuerde,
- die Kompetenz in jahrgangsgemischten Lerngruppen sinnvoll gemeinsam beobachtet wird.

Stufenuebergreifend bedeutet nicht ungenau. Die Kompetenz muss weiterhin konkret beobachtbar und lehrplanbezogen begruendet sein.

## Bestandsschutz

Bestehende Kompetenz-IDs werden nicht veraendert.

Bestehende Beobachtungen werden nicht migriert.

Alte Kompetenzdefinitionen werden durch die Stufenlogik nicht automatisch umgedeutet.

## Offene technische Umsetzung

Noch offen:

- in welchem technischen Feld die Stufe spaeter gespeichert wird,
- ob die CSV eine neue Spalte erhaelt,
- ob SQLite erweitert wird,
- wie die Filter im Beobachtungsdialog umgesetzt werden,
- wie stufenuebergreifende Kompetenzen in der UI markiert werden.

Bis zur ausdruecklichen technischen Freigabe gilt diese Datei nur als fachliche Grundlage.
