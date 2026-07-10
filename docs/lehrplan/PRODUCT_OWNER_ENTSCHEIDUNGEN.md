# Product-Owner-Entscheidungen fuer Sprint 4

Status: Entscheidungsvorlage fuer Product Owner. Keine CSV-Aenderung, keine Code-Aenderung, keine SQLite-Aenderung, keine Migration, keine ID-Vergabe, keine aktuelle Deaktivierung.

## Product-Owner-Freigabe

Stand: Sprint 4 abgeschlossen

Die Product-Owner-Entscheidungen 1-13 sowie Entscheidung 16 wurden fachlich freigegeben.

Die Entscheidungen 14, 15, 17 und 18 bleiben bewusst fuer spaetere Sprints offen.

## Pruefumfang

Ausgewertet wurden ausschliesslich:

- `docs/lehrplan/KATALOG_KONSOLIDIERUNG.md`
- `docs/lehrplan/KATALOG_DIFFERENZBERICHT.md`
- `docs/lehrplan/MAPPING_REGELN.md`
- `docs/lehrplan/STUFENZUORDNUNG.md`
- `docs/lehrplan/mapping/DEUTSCH_MAPPING.md`
- `docs/lehrplan/mapping/ETHIK_MAPPING.md`
- `docs/lehrplan/mapping/HEIMAT_SACHKUNDE_MAPPING.md`
- `docs/lehrplan/mapping/KUNST_MAPPING.md`
- `docs/lehrplan/mapping/MATHEMATIK_MAPPING.md`
- `docs/lehrplan/mapping/MUSIK_MAPPING.md`
- `docs/lehrplan/mapping/SCHULGARTEN_MAPPING.md`
- `docs/lehrplan/mapping/SPORT_MAPPING.md`
- `docs/lehrplan/mapping/WERKEN_MAPPING.md`

## Prioritaeten

- P1: muss vor CSV-Erstellung entschieden werden
- P2: sollte vor Sprint 5 entschieden werden
- P3: kann spaeter entschieden werden

## Abgeschlossene Grundsatzentscheidungen

- Deutsch-Quelle: Die verwendete Quelle `lp_gs_D_2010_2012.pdf` ist dokumentiert und fuer Sprint 4 fachlich freigegeben. Diese Frage wird nicht mehr als offene Product-Owner-Entscheidung gefuehrt.

## Entscheidung 1: Definition einer beobachtbaren Kompetenz

Prioritaet: P1

Betroffene Faecher: Deutsch, Mathematik, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Schulgarten, Sport, Werken

Hintergrund: Fuer alle spaeteren Katalogentscheidungen braucht es einen verbindlichen fachlichen Massstab, damit nur solche Inhalte als eigenstaendige Kompetenzen entstehen, die im Unterricht wirklich separat beobachtet und bewertet werden koennen.

Verbindliche Produktentscheidung: Eine Kompetenz wird nur dann als eigenstaendige Kompetenz in den Kompetenzkatalog aufgenommen, wenn sie von einer Lehrkraft in einer konkreten Unterrichtssituation unabhaengig beobachtet und sinnvoll mit `++`, `+`, `-` oder `--` bewertet werden kann.

Keine eigenstaendigen Kompetenzen sind beispielsweise:

- Haltungen
- Einstellungen
- Emotionen
- Wuensche
- Unterrichtshinweise
- reine Sicherheitsregeln ohne beobachtbare Fachhandlung
- Methoden ohne Fachbezug

Moegliche Optionen:

- Streng nur unabhaengig beobachtbare und bewertbare Fachhandlungen als Kompetenzen aufnehmen.
- Auch Haltungen, Einstellungen, Methoden oder Sicherheitsregeln als eigene Kompetenzen aufnehmen.
- Grenzfaelle je Fach ohne gemeinsame Grundregel entscheiden.

Empfehlung: Streng nur unabhaengig beobachtbare und bewertbare Fachhandlungen als eigenstaendige Kompetenzen aufnehmen.

Auswirkungen auf den Kompetenzkatalog: Diese Regel ist zukuenftig der fachliche Massstab fuer alle Katalogentscheidungen und verhindert Haltungs-, Methoden- oder Sicherheitszeilen ohne beobachtbare Fachhandlung.

Auswirkungen auf Bestandsschutz: Bestehende Eintraege bleiben historisch geschuetzt; die Definition steuert neue oder konsolidierte Katalogentscheidungen.

Auswirkungen auf spaetere CSV-Generierung: Nur Inhalte, die diese Definition erfuellen, duerfen spaeter eigenstaendige CSV-Kompetenzzeilen erzeugen.

Auswirkungen auf UI oder Dokumentationsstand: Die UI zeigt bewertbare Kompetenzen getrennt von Hinweisen, Haltungen oder unbewerteten Kontexten. Dokumentationshinweise duerfen nicht wie Kompetenzbewertungen wirken.

Empfohlene Standardentscheidung: Definition verbindlich anwenden.

## Entscheidung 2: Stufenmodell fuer Kompetenzzeilen festlegen

Prioritaet: P1

Betroffene Faecher: Deutsch, Mathematik, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Schulgarten, Sport, Werken

Hintergrund: Die Unterlagen unterscheiden `Klassenstufe 1-3`, `Klassenstufe 4` und `stufenuebergreifend`. Mehrere Faecher enthalten dieselbe fachliche Linie mit unterschiedlicher Tiefe, Selbststaendigkeit oder Komplexitaet.

Moegliche Optionen:

- Gemeinsame Kompetenz mit Niveauhinweis.
- Getrennte Kompetenzzeilen fuer Schuleingangsphase und Klassenstufe 4.
- Fachweise Mischentscheidung: getrennt bei neuem Gegenstand oder Verfahren, gemeinsam bei gleicher Beobachtungssituation.

Empfehlung: Fachweise Mischentscheidung. Trennen, wenn Gegenstand, Verfahren, Produkt oder Foerderentscheidung wechseln; sonst gemeinsame Kompetenz mit Niveauhinweis.

Verbindliche Produktentscheidung fuer die spaetere UI:

- Standard: `Passende Kompetenzen`
- Filter: `Klassenstufe 1-3`
- Filter: `Klassenstufe 4`
- Optional: `Alle Kompetenzen anzeigen`

Kompetenzen werden niemals gesperrt, sondern lediglich gefiltert.

Auswirkungen auf den Kompetenzkatalog: Verhindert doppelte oder kuenstlich getrennte Zeilen und erhaelt fachlich echte Progression.

Auswirkungen auf Bestandsschutz: Bestehende Kompetenzen werden dadurch nicht umgedeutet und nicht migriert.

Auswirkungen auf spaetere CSV-Generierung: Vor der CSV-Erstellung muss klar sein, ob eine Sollkompetenz eine oder zwei CSV-Zeilen erzeugt.

Auswirkungen auf UI oder Dokumentationsstand: Die spaetere UI nutzt `Passende Kompetenzen` als Standard, bietet Filter fuer `Klassenstufe 1-3` und `Klassenstufe 4` sowie optional `Alle Kompetenzen anzeigen`. Jahrgangsgemischte Gruppen behalten Zugriff, weil Kompetenzen nie gesperrt werden.

Empfohlene Standardentscheidung: Mischentscheidung nach fachlicher Beobachtungssituation.

## Entscheidung 3: Bestandsschutz fuer vorhandene Katalogeintraege bestaetigen

Prioritaet: P1

Betroffene Faecher: Deutsch, Mathematik, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Schulgarten, Sport, Werken; ausserdem bestehende Sozialkompetenz- und Religionsbestaende ohne Mapping im Pruefumfang

Hintergrund: Der Differenzbericht beschreibt alte grobe, zu feine oder nicht eindeutig belegte Bestandseintraege. Bestehende Beobachtungen und Kompetenzbewertungen referenzieren diese historischen Eintraege.

Moegliche Optionen:

- Bestandseintraege historisch behalten und neue konkrete Sollkompetenzen ergaenzen.
- Bestandseintraege fachlich umbenennen oder umdeuten.
- Bestandseintraege spaeter deaktivieren, aber erst nach separater Freigabe.

Empfehlung: Historisch behalten, nicht umdeuten, nicht automatisch migrieren. Spaetere Deaktivierung nur als eigener Product-Owner-Prozess.

Auswirkungen auf den Kompetenzkatalog: Neue fachliche Praezision entsteht durch Ergaenzung, nicht durch Umbenennung alter Bedeutung.

Auswirkungen auf Bestandsschutz: Maximale Wahrung bestehender Beobachtungen und Bewertungen.

Auswirkungen auf spaetere CSV-Generierung: Neue konkrete Kompetenzen brauchen neue spaetere Katalogzeilen; vorhandene Zeilen duerfen nicht fuer neue Inhalte wiederverwendet werden.

Auswirkungen auf UI oder Dokumentationsstand: Alte Beobachtungen bleiben lesbar. Spaetere Filter duerfen historische Eintraege nicht ausblenden, wenn dadurch vorhandene Dokumentation unauffindbar wird.

Empfohlene Standardentscheidung: Bestandsschutz bestaetigen.

## Entscheidung 4: Sozialkompetenz klar vom Fachkatalog trennen

Prioritaet: P1

Betroffene Faecher: Deutsch, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Sport

Hintergrund: Viele Mapping-Zeilen enthalten Kooperation, Gespraechsregeln, Ruecksichtnahme, Perspektivwechsel, Fair Play, Gruppenhandeln, Konfliktklaerung oder Partnerbezug. Diese Punkte sind fachlich nur dann Katalogkompetenzen, wenn die fachliche Leistung im Vordergrund steht.

Moegliche Optionen:

- Solche Punkte in den jeweiligen Fachkatalog aufnehmen.
- Solche Punkte grundsaetzlich in einen separaten Sozialkompetenz-Katalog verschieben.
- Nur fachlich gebundene Anteile im Fachkatalog belassen und reine Interaktionsanteile separat fuehren.

Empfehlung: Fachlich gebundene Anteile im Fachkatalog belassen; reine Sozial-, Kooperations- und Haltungsanteile separat fuehren.

Auswirkungen auf den Kompetenzkatalog: Der Fachkatalog bleibt beobachtbar und fachlich begrenzt. Sozialkompetenzen werden nicht in Deutsch, Ethik, Sport oder EPU versteckt.

Auswirkungen auf Bestandsschutz: Bestehende Fach- und Sozialkompetenzen bleiben unveraendert. Die Entscheidung steuert nur spaetere neue Sollzeilen.

Auswirkungen auf spaetere CSV-Generierung: Vor CSV-Erstellung muss je Grenzfall entschieden sein, ob eine Fachzeile entsteht oder ein separater Sozialkompetenz-Eintrag vorbereitet wird.

Auswirkungen auf UI oder Dokumentationsstand: Die UI kann Fachbeobachtungen und soziale Entwicklungsbeobachtungen spaeter klarer trennen.

Empfohlene Standardentscheidung: Fachkatalog nur bei klarem Fachgegenstand.

## Entscheidung 5: Haltungsziele und Innenperspektiven nicht als Fachbewertung fuehren

Prioritaet: P1

Betroffene Faecher: Deutsch, Heimat- und Sachkunde / EPU, Ethik, Kunst, Sport, Schulgarten

Hintergrund: Die Unterlagen nennen Selbstwert, Einmaligkeit, Empathie, Wertschaetzung, Respekt, Toleranz, Heimatgefuehl, regionale Zugehoerigkeit, Freude, Genuss, Vorlieben, Umgang mit Sieg und Niederlage sowie allgemeine Natur- oder Verantwortungs-Haltung.

Moegliche Optionen:

- Als bewertbare Fachkompetenzen aufnehmen.
- Als Sozialkompetenzen bewertbar machen.
- Als qualitative Beobachtungs- oder Entwicklungsnotizen dokumentieren.

Empfehlung: Nicht als Fachbewertung aufnehmen. Nur dann bewerten, wenn eine beobachtbare fachliche Handlung, Argumentation oder Produktleistung vorliegt; sonst qualitativ dokumentieren.

Auswirkungen auf den Kompetenzkatalog: Verhindert Bewertungen innerer Haltungen ohne belastbaren Beobachtungsanker.

Auswirkungen auf Bestandsschutz: Keine Umdeutung bestehender Eintraege; spaetere Haltungsnotizen duerfen alte Bewertungen nicht ersetzen.

Auswirkungen auf spaetere CSV-Generierung: Entsprechende Mapping-Zeilen erzeugen keine Fachkompetenzzeilen, sondern bleiben Hinweise oder werden in einen separaten Bereich verschoben.

Auswirkungen auf UI oder Dokumentationsstand: Dokumentationssprache muss ruhig und nicht defizitorientiert bleiben. Haltungsaspekte sollten nicht wie benotete Fachleistungen erscheinen.

Empfohlene Standardentscheidung: Qualitativ dokumentieren, nicht fachlich bewerten.

## Entscheidung 6: Sexualerziehung und Radfahrausbildung fachlich bewerten

Prioritaet: P1

Betroffene Faecher: Heimat- und Sachkunde / EPU

Hintergrund: Sexualerziehung und praktische Radfahrausbildung sind im Mapping als besondere Pruefpunkte markiert. Die Product-Owner-Entscheidung stellt klar, dass solche Inhalte nicht pauschal unbewertbar sind. Bewertbar ist jedoch nur, was konkret beobachtbar oder als Sachkompetenz nachweisbar ist.

Verbindliche Produktentscheidung: Inhalte wie Sexualerziehung oder Radfahrausbildung werden nicht pauschal als unbewertbar behandelt.

Bewertet werden ausschliesslich konkret beobachtbare fachliche Handlungen oder nachweisbare Sachkompetenzen.

Nicht bewertet werden:

- reine Teilnahme
- persoenliche Einstellungen
- Haltungen
- Emotionen
- innere Entwicklungen

Beispiele fuer bewertbare Kompetenzen:

- kennt wichtige Verkehrsregeln
- fuehrt das Fahrrad im Uebungsparcours sicher
- erklaert Schutzmassnahmen

Beispiele fuer nicht bewertbare Inhalte:

- hat an der Radfahrausbildung teilgenommen
- zeigt eine verantwortungsvolle Haltung

Moegliche Optionen:

- Als regulare bewertbare Fachkompetenzen aufnehmen.
- Pauschal als unbewertete Unterrichts- oder Beobachtungshinweise fuehren.
- Nur konkret beobachtbare Fachhandlungen und nachweisbare Sachkompetenzen als bewertbare Kompetenzzeilen fuehren.

Empfehlung: Nur konkret beobachtbare Fachhandlungen und nachweisbare Sachkompetenzen als bewertbare Kompetenzzeilen fuehren.

Auswirkungen auf den Kompetenzkatalog: Fachlich beobachtbare Verkehrs-, Schutz- oder Sachkompetenzen koennen in den Katalog aufgenommen werden. Teilnahme, Haltung und innere Entwicklung erzeugen keine eigenstaendigen Kompetenzzeilen.

Auswirkungen auf Bestandsschutz: Keine automatische Anpassung bestehender Gesundheits-, Verkehrs- oder EPU-Eintraege.

Auswirkungen auf spaetere CSV-Generierung: Spaetere CSV-Zeilen duerfen nur fuer beobachtbare Fachhandlungen oder nachweisbare Sachkompetenzen entstehen.

Auswirkungen auf UI oder Dokumentationsstand: Die UI darf Teilnahme- oder Haltungsformulierungen nicht wie bewertbare Kompetenzen darstellen. Fachlich beobachtbare Handlungen koennen regulaer bewertet werden.

Empfohlene Standardentscheidung: Fachhandlung oder Sachkompetenz bewerten; Teilnahme, Haltung, Emotion und innere Entwicklung nicht bewerten.

## Entscheidung 7: Sicherheits-, Schutz- und Arbeitsschutzaspekte behandeln

Prioritaet: P1

Betroffene Faecher: Heimat- und Sachkunde / EPU, Schulgarten, Sport, Werken

Hintergrund: Alarm, Notruf, Erste Hilfe, Verkehrssicherheit, Arbeitsschutz, Unfallverhuetung, Werkzeugumgang, Hygiene, Sichern, Helfen und Funktionssicherheit tauchen in mehreren Faechern auf. Teilweise sind sie fachlich an praktische Handlung gebunden, teilweise reine Schutzstandards.

Moegliche Optionen:

- Eigene bewertbare Katalogzeilen je Sicherheitsaspekt.
- Verbindliche Beobachtungshinweise an praktischen Fachkompetenzen.
- Nicht benotete Schutzstandards ausserhalb des Kompetenzkatalogs.

Empfehlung: Als eigene Kompetenz nur fuehren, wenn eine fachliche Handlung beobachtet wird. Reine Schutz- und Regelstandards als verbindliche Hinweise dokumentieren.

Auswirkungen auf den Kompetenzkatalog: Sicherheitsaspekte ueberfrachten den Katalog nicht, bleiben aber im Unterricht sichtbar.

Auswirkungen auf Bestandsschutz: Bestehende Sicherheits- oder Werkzeugkompetenzen bleiben erhalten; spaetere Praezisierung erfolgt ergaenzend.

Auswirkungen auf spaetere CSV-Generierung: Vor CSV-Erstellung muss entschieden sein, ob ein Sicherheitsaspekt eine Zeile erzeugt oder nur als Hinweis an einer Fachkompetenz haengt.

Auswirkungen auf UI oder Dokumentationsstand: Hinweise duerfen nicht wie bewertbare Kompetenzen erscheinen. Praktische Faechern brauchen dennoch sichtbare Sicherheitskontexte.

Empfohlene Standardentscheidung: Fachlich gebundene Sicherheit bewerten, reine Schutzstandards als Hinweis fuehren.

## Entscheidung 8: Methoden, Werkzeuge, Recherche und Praesentation nur fachgebunden fuehren

Prioritaet: P1

Betroffene Faecher: Deutsch, Mathematik, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Schulgarten, Sport, Werken

Hintergrund: Die Mapping-Dateien enthalten Woerterbuchnutzung, Mess- und Zeichengeraete, Gartengeraete, Werkzeuge, Medienrecherche, Interviews, Mindmaps, Aufgabenanalyse, Praesentation und Prozessdarstellung. Die Regeln verlangen einen fachlichen Gegenstand oder ein Produkt.

Moegliche Optionen:

- Methoden und Werkzeuge als eigene Kompetenzzeilen fuehren.
- Methoden immer als Beobachtungshinweise an Sachkompetenzen haengen.
- Eigene Zeile nur bei fachlicher Schuelerhandlung mit Produkt, Begruendung oder Anwendung.

Empfehlung: Eigene Zeile nur bei fachlich sichtbarer Leistung; sonst Beobachtungshinweis.

Auswirkungen auf den Kompetenzkatalog: Verhindert technische Abhakpunkte und haelt Methoden an fachliche Lerngegenstaende gebunden.

Auswirkungen auf Bestandsschutz: Bestehende methodische Bestandskompetenzen bleiben sichtbar, werden aber nicht fuer neue Fachinhalte umgedeutet.

Auswirkungen auf spaetere CSV-Generierung: Generische Methoden erzeugen keine eigenstaendigen CSV-Zeilen. Fachgebundene Methoden koennen in konkrete Kompetenzformulierungen einfliessen.

Auswirkungen auf UI oder Dokumentationsstand: Beobachtungshinweise koennen Lehrkraeften Kontext geben, ohne die Bewertungslisten aufzublaehen.

Empfohlene Standardentscheidung: Methoden fachgebunden, nicht generisch.

## Entscheidung 9: Medien, Medienprodukte und Medienkonsum einordnen

Prioritaet: P1

Betroffene Faecher: Deutsch, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik

Hintergrund: Medien erscheinen als Recherchemittel, Praesentationsmittel, Medienprodukt, Medienkonsum-Selbstreflexion, Musikmedien, szenische oder bildnerische Darstellung und Lese-/Arbeitshilfe.

Moegliche Optionen:

- Ein eigenes medienbezogenes Thema je Fach fuehren.
- Mediennutzung grundsaetzlich als Methode an Fachkompetenzen haengen.
- Nur Medienanalyse und produktbezogene Mediengestaltung als eigene Kompetenz fuehren.

Empfehlung: Medien nur eigenstaendig fuehren, wenn Analyse, Gestaltung oder Produkt fachlich bewertet wird. Reine Nutzung oder Technik bleibt Beobachtungshinweis.

Auswirkungen auf den Kompetenzkatalog: Medienkompetenz bleibt fachlich pruefbar und wird nicht mit Geraetenutzung verwechselt.

Auswirkungen auf Bestandsschutz: Bestehende medienbezogene Eintraege bleiben erhalten; neue Medienzeilen werden nur fachlich begruendet ergaenzt.

Auswirkungen auf spaetere CSV-Generierung: Vor CSV-Erstellung muss je Medienzeile entschieden sein, ob sie eine Fachkompetenz, ein Hinweis oder ein ueberfachlicher Reflexionspunkt ist.

Auswirkungen auf UI oder Dokumentationsstand: Medienkonsum-Selbstreflexion sollte nicht als harte Fachnote erscheinen, wenn kein fachliches Analyseprodukt vorliegt.

Empfohlene Standardentscheidung: Eigenstaendig nur bei Medienanalyse oder Medienprodukt.

## Entscheidung 10: Granularitaet grosser und kleiner Fachkompetenzen festlegen

Prioritaet: P1

Betroffene Faecher: Deutsch, Mathematik, Kunst, Werken, Heimat- und Sachkunde / EPU, Musik, Sport

Hintergrund: Die Berichte markieren sehr breite Buendel und sehr kleine Einzelbeispiele. Beispiele sind Schreibprozess, Texterschliessung, Sprachreflexion, Kontextaufgaben, Koerper/Flaechen, Gestaltungszeilen, Werkstofffertigung, Uhrzeit-Einzelpunkte, einzelne Musikzeichen oder einzelne Bewegungsleistungen.

Moegliche Optionen:

- Grobe Buendel als wenige Kompetenzzeilen fuehren.
- Stark in Teilhandlungen zerlegen.
- Nur trennen, wenn unterschiedliche Beobachtungssituationen oder Foerderentscheidungen entstehen.

Empfehlung: Trennung nur bei anderer Beobachtungssituation, anderem Produkt, anderem Verfahren oder anderer Foerderentscheidung.

Auswirkungen auf den Kompetenzkatalog: Der Katalog bleibt fuer Lehrkraefte nutzbar und vermeidet sowohl Sammelbewertungen als auch Kleinstabhaken.

Auswirkungen auf Bestandsschutz: Alte grobe und feine Eintraege bleiben historisch erhalten; neue Zeilen bilden die konsolidierte Fachlogik ab.

Auswirkungen auf spaetere CSV-Generierung: Diese Entscheidung bestimmt direkt Anzahl und Zuschnitt spaeterer CSV-Zeilen.

Auswirkungen auf UI oder Dokumentationsstand: Eine passend granulare Liste reduziert Ueberladung im Beobachtungsdialog.

Empfohlene Standardentscheidung: Beobachtungssituation und Foerderentscheidung als Trennkriterium nutzen.

## Entscheidung 11: Umwelt, Naturverantwortung, Nachhaltigkeit und Energie fachlich verorten

Prioritaet: P1

Betroffene Faecher: Heimat- und Sachkunde / EPU, Ethik, Schulgarten, Werken

Hintergrund: Naturschutz, Naturverantwortung, nachhaltige Kulturfuehrung, sparsame Ressourcennutzung, Recycling, Umweltveraenderungen und Energiesparen liegen fachlich nah beieinander, aber mit unterschiedlichem Schwerpunkt.

Moegliche Optionen:

- Je Fach eigene Kompetenzzeilen fuehren.
- Ueberfachlichen Nachhaltigkeitsbereich vorbereiten.
- Fachlich nur dort fuehren, wo Handlung, Analyse oder Produkt klar zum Fach gehoert.

Empfehlung: Fachlich nur dort fuehren, wo der Fachgegenstand klar ist: HSK/EPU fuer Sachanalyse, Ethik fuer Urteilsbildung, Schulgarten fuer Gartenhandlung, Werken fuer produkt- oder technikbezogenen Bezug.

Auswirkungen auf den Kompetenzkatalog: Vermeidet Mehrfachbewertungen derselben Haltung und haelt fachliche Unterschiede sichtbar.

Auswirkungen auf Bestandsschutz: Keine Veraenderung bestehender Umwelt- oder Verantwortungszeilen.

Auswirkungen auf spaetere CSV-Generierung: Aehnliche Nachhaltigkeitsformulierungen duerfen nicht mehrfach als identische Fachkompetenzen entstehen.

Auswirkungen auf UI oder Dokumentationsstand: Dokumentation sollte den Fachfokus sichtbar machen, damit Umweltaspekte nicht als allgemeine Haltung bewertet werden.

Empfohlene Standardentscheidung: Fachbezogene Verortung nach Handlungstyp.

## Entscheidung 12: Lehrplanbasierte Sportbereiche vollstaendig erhalten

Prioritaet: P1

Betroffene Faecher: Sport

Hintergrund: Der Sport-Lehrplan enthaelt neben regelmaessig genutzten Bewegungsfeldern auch optional unterrichtete Bereiche wie Ski, Eislaufen und Inline-Skating. Der Katalog soll fachlich vollstaendig bleiben, ohne Lehrkraefte im Alltag mit nicht genutzten Bereichen zu belasten.

Verbindliche Produktentscheidung: Alle lehrplanbasierten Sportbereiche bleiben fachlich Bestandteil des Kompetenzkatalogs.

Optional unterrichtete Bereiche, zum Beispiel Ski, Eislaufen und Inline-Skating, werden standardmaessig deaktiviert und koennen spaeter ueber die Einstellungen aktiviert werden.

Dadurch bleibt der Kompetenzkatalog vollstaendig, ohne Lehrkraefte mit nicht genutzten Bereichen zu belasten.

Moegliche Optionen:

- Alle lehrplanbasierten Sportbereiche regulaer sichtbar aufnehmen.
- Nur die an Lauras Schule real unterrichteten Bereiche aufnehmen.
- Alle lehrplanbasierten Sportbereiche aufnehmen und optional unterrichtete Bereiche standardmaessig deaktivieren.

Empfehlung: Alle lehrplanbasierten Sportbereiche fachlich im Katalog behalten und optional unterrichtete Bereiche standardmaessig deaktivieren.

Auswirkungen auf den Kompetenzkatalog: Der Sportkatalog bleibt lehrplanvollstaendig. Optional unterrichtete Bereiche gehoeren fachlich dazu, erscheinen aber nicht automatisch im Arbeitsalltag.

Auswirkungen auf Bestandsschutz: Bestehende Sporteintraege bleiben erhalten.

Auswirkungen auf spaetere CSV-Generierung: Alle lehrplanbasierten Sportbereiche koennen spaeter als Katalogbestand vorbereitet werden. Fuer optional unterrichtete Bereiche braucht die spaetere technische Umsetzung eine Aktivierungslogik.

Auswirkungen auf UI oder Dokumentationsstand: Die UI braucht spaeter Einstellungen, mit denen optional unterrichtete Sportbereiche aktiviert werden koennen. Standardmaessig bleiben diese Bereiche deaktiviert.

Empfohlene Standardentscheidung: Vollstaendig aufnehmen, optional unterrichtete Bereiche standardmaessig deaktivieren.

## Entscheidung 13: Szenisches Spiel, Spielhandlungen und Darstellung verorten

Prioritaet: P1

Betroffene Faecher: Deutsch, Kunst, Musik, Heimat- und Sachkunde / EPU, Sport

Hintergrund: Szenisches Spiel, Rollenspiel, Darstellung mit Figuren, Bewegung zu Musik, Tanz, Medien-/Darstellungsprodukte und kooperative Spielhandlungen erscheinen in mehreren Faechern. Der fachliche Kern wechselt zwischen Sprache, Gestaltung, Musik, Medien, Bewegung und Sozialverhalten.

Moegliche Optionen:

- Alle Darstellungsformen als Fachkompetenzen im jeweiligen Fach fuehren.
- Darstellungsformen nur bei fachlichem Produkt oder fachlicher Wirkung fuehren.
- Kooperative oder soziale Spielanteile in Sozialkompetenz-Hinweise verschieben.

Empfehlung: Fachkompetenz nur bei fachlichem Produkt, Ausdrucksmittel oder Deutungsleistung; soziale Spielanteile separat dokumentieren.

Auswirkungen auf den Kompetenzkatalog: Verhindert Doppelungen zwischen Deutsch, Kunst, Musik, HSK/EPU und Sport.

Auswirkungen auf Bestandsschutz: Bestehende Darstellungs- oder Spielkompetenzen bleiben unveraendert.

Auswirkungen auf spaetere CSV-Generierung: Vor CSV-Erstellung muss je Darstellungszeile klar sein, welchem Fachgegenstand sie dient.

Auswirkungen auf UI oder Dokumentationsstand: Lehrkraefte sehen spaeter klarer, ob Sprache, Gestaltung, Musik, Bewegung oder Sozialverhalten bewertet wird.

Empfohlene Standardentscheidung: Fachliche Darstellung bewerten, kooperative Spielanteile als Hinweis.

## Entscheidung 14: UI-Darstellung fuer unbewertete Hinweise vorbereiten

Prioritaet: P2

Betroffene Faecher: Heimat- und Sachkunde / EPU, Ethik, Schulgarten, Sport, Werken; bei Bedarf alle Faecher

Hintergrund: Mehrere Entscheidungen fuehren zu Inhalten, die fachlich wichtig sind, aber nicht als normale Entwicklungsbewertung erscheinen sollen: Schutzstandards, Haltungsziele, Sexualerziehung, Radfahrausbildung, Sicherheitskontexte und reine Beobachtungshinweise.

Moegliche Optionen:

- Solche Inhalte in regulaeren Kompetenzlisten anzeigen.
- Solche Inhalte gar nicht anzeigen.
- Eigene Darstellung als Hinweis, Unterrichtsnotiz oder nicht bewertbarer Kontext.

Empfehlung: Eigene, klar nicht bewertbare Darstellung vorbereiten.

Auswirkungen auf den Kompetenzkatalog: Der Katalog kann fachliche Hinweise enthalten, ohne sie zu bewertbaren Kompetenzen zu machen.

Auswirkungen auf Bestandsschutz: Bestehende Bewertungen bleiben getrennt von neuen Hinweisen.

Auswirkungen auf spaetere CSV-Generierung: CSV-Erstellung muss ggf. zwischen Kompetenzzeilen und Hinweistexten unterscheiden; konkrete technische Umsetzung bleibt spaeter.

Auswirkungen auf UI oder Dokumentationsstand: UI und Dokumentation brauchen eine eindeutige Sprache, damit Hinweise nicht als Kompetenzbewertung verstanden werden.

Empfohlene Standardentscheidung: Nicht bewertbare Hinweise separat darstellen.

## Entscheidung 15: Struktur fuer separaten Sozialkompetenz-Katalog vorbereiten

Prioritaet: P2

Betroffene Faecher: Deutsch, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Sport

Hintergrund: Wenn Sozialkompetenzen aus den Fachkatalogen herausgenommen werden, braucht der separate Sozialkompetenz-Katalog eine fachlich tragfaehige Struktur. Sonst gehen wichtige Entwicklungsaspekte verloren oder wandern spaeter ungeordnet in Fachzeilen zurueck.

Moegliche Optionen:

- Sozialkompetenzstruktur sofort fachlich ausarbeiten.
- Sozialkompetenzstruktur als eigenes Sprint-5-Thema planen.
- Sozialkompetenzen bis dahin als Hinweise in den Fachunterlagen belassen.

Empfehlung: Als eigenes Sprint-5-Thema planen; bis dahin fachliche Grenzfaelle dokumentieren, aber nicht in Fach-CSV erzwingen.

Auswirkungen auf den Kompetenzkatalog: Fachkataloge bleiben bereinigt, waehrend Sozialkompetenzen nicht verloren gehen.

Auswirkungen auf Bestandsschutz: Bestehende Sozialkompetenzbestaende bleiben geschuetzt.

Auswirkungen auf spaetere CSV-Generierung: Fach-CSV kann ohne verdeckte Sozialkompetenzzeilen entstehen. Ein separater Sozialkompetenz-Import braucht spaeter eigene Freigabe.

Auswirkungen auf UI oder Dokumentationsstand: Spaeter kann die UI Fach- und Sozialbeobachtungen getrennt, aber gemeinsam im Schuelerprofil anzeigen.

Empfohlene Standardentscheidung: Eigenes Sprint-5-Thema.

## Entscheidung 16: Umsetzungspakete fuer die Katalogarbeit priorisieren

Prioritaet: P2

Betroffene Faecher: Deutsch, Mathematik, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Schulgarten, Sport, Werken

Hintergrund: Die Differenz zwischen Bestand und Soll ist gross. Die Unterlagen schlagen Pakete fuer Bestandsschutz, Stufenentscheidung, Kernfaecher, EPU, Ethik/Sozialkompetenz, Kuenste/Musik, Sport sowie Werken/Schulgarten vor.

Moegliche Optionen:

- Alle Faecher gleichzeitig in CSV-Arbeit ueberfuehren.
- Nach Fachpaketen und Risiko priorisieren.
- Nur Kernfaecher bearbeiten und Nebenfaecher spaeter verschieben.

Empfehlung: Nach Paketen und Risiko priorisieren: zuerst Bestandsschutz und Stufe, dann Deutsch/Mathematik, danach EPU und Ethik/Sozialkompetenz, anschliessend Kuenste/Musik, Sport, Werken/Schulgarten.

Auswirkungen auf den Kompetenzkatalog: Die Katalogarbeit bleibt pruefbar und fachlich beherrschbar.

Auswirkungen auf Bestandsschutz: Bestandsschutz wird vor jedem Fachpaket erneut geprueft.

Auswirkungen auf spaetere CSV-Generierung: CSV kann paketweise vorbereitet werden, ohne unfertige Faecher halb umzusetzen.

Auswirkungen auf UI oder Dokumentationsstand: Dokumentationsstand kann pro Paket transparent nachgezogen werden.

Empfohlene Standardentscheidung: Paketweise nach Risiko vorgehen.

## Entscheidung 17: Spaetere Deaktivierung alter grober Eintraege separat entscheiden

Prioritaet: P3

Betroffene Faecher: Deutsch, Mathematik, Heimat- und Sachkunde / EPU, Ethik, Kunst, Musik, Schulgarten, Sport, Werken

Hintergrund: Der Differenzbericht markiert alte grobe Eintraege als moegliche spaetere Deaktivierung oder Archivierung. Fuer Sprint 4 ist jedoch keine Deaktivierung vorgesehen.

Moegliche Optionen:

- Alte grobe Eintraege nach neuen Sollzeilen deaktivieren.
- Alte grobe Eintraege dauerhaft sichtbar lassen.
- Alte grobe Eintraege nur in neuen Beobachtungen ausblenden, aber in historischen Ansichten sichtbar halten.

Empfehlung: Spaeter separat entscheiden; bis dahin alte Eintraege sichtbar und historisch geschuetzt lassen.

Auswirkungen auf den Kompetenzkatalog: Keine unmittelbare Aenderung. Spaeter kann der aktive Katalog verschlankt werden.

Auswirkungen auf Bestandsschutz: Historische Beobachtungen bleiben sichtbar und unveraendert.

Auswirkungen auf spaetere CSV-Generierung: Keine Voraussetzung fuer die erste neue CSV-Erstellung, solange neue Sollzeilen ergaenzend entstehen.

Auswirkungen auf UI oder Dokumentationsstand: Spaeter braucht es ggf. aktive/archivierte Darstellung, damit alte Bewertungen nicht verschwinden.

Empfohlene Standardentscheidung: Jetzt nicht deaktivieren.

## Entscheidung 18: Textnormalisierung fuer spaetere CSV klaeren

Prioritaet: P3

Betroffene Faecher: Mathematik; bei spaeterer CSV-Erstellung potentiell alle Faecher

Hintergrund: Das Mathematik-Mapping nennt die Frage, ob Begriffe mit Umlauten im spaeteren CSV technisch normalisiert werden sollen. Die aktuellen Mapping-Dateien bleiben fachlich lesbar.

Moegliche Optionen:

- Fachtexte mit Umlauten und Originalschreibung uebernehmen.
- Fachtexte technisch normalisieren.
- Nur technische Schluessel normalisieren, sichtbare Fachtexte fachlich lesbar lassen.

Empfehlung: Sichtbare Fachtexte fachlich lesbar lassen; technische Normalisierung nur fuer spaetere technische Schluessel pruefen.

Auswirkungen auf den Kompetenzkatalog: Fachliche Lesbarkeit bleibt erhalten.

Auswirkungen auf Bestandsschutz: Keine Auswirkung auf bestehende Eintraege.

Auswirkungen auf spaetere CSV-Generierung: Betrifft spaeter nur Text- und Schluesselformate, nicht die fachliche Entscheidung, welche Kompetenzen entstehen.

Auswirkungen auf UI oder Dokumentationsstand: Sichtbare UI-Texte sollten fachlich natuerlich und lehrkraeftetauglich bleiben.

Empfohlene Standardentscheidung: Sichtbare Fachtexte nicht technisch verkuerzen.

## Zaehler

- Anzahl zusammengefasster Entscheidungen: 18
- Anzahl P1: 13
- Anzahl P2: 3
- Anzahl P3: 2

## Bewusst nicht geaendert

- Keine bestehenden Mapping-Dateien
- Keine CSV-Dateien
- Kein Code
- Keine SQLite-Datei
- Keine Migration
- Keine bestehenden Kompetenz-IDs
- Keine aktuellen Deaktivierungen
- Kein Commit
