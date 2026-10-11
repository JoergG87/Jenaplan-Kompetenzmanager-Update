# Design-System

## Cipher-Produktmodus

Die Aktivierung verwendet ausschließlich vorhandene Oberflächen. Nach der
Authentifizierung öffnet die App normal; Schlüssel-, Envelope-, Pfad- und
Engineinformationen bleiben technisch und unsichtbar. Ein Startupfehler wird
ruhig und sanitisiert dargestellt und bietet keine Migration, automatische
Reparatur oder Klartextübernahme an.

Backup und Restore verwenden die vorhandene ruhige Datensicherungsansicht.
Im Cipher-Produktmodus akzeptieren Dateiauswahl und Status ausschließlich
`.jkmebackup`; die Vorschau benennt den vollständig vorbereiteten Zustand als
`Sicher zur Wiederherstellung vorbereitet (RESTORE_READY)`. Fehlertexte
unterscheiden Erzeugung, Manipulation, Installations-/Schlüsselkontext,
Staging und Worker-Übergabe, ohne technische IDs, Pfade, Hashes oder
Exceptions anzuzeigen. Der frühere geführte ZIP-v1-Testdaten-Restore wird im
Cipher-Produktmodus nicht angeboten.

## SJ-1 - UX-Vertrag für den Schuljahresassistenten

**Status:** Verbindlicher Zielvertrag. SJ-3B.1 setzt die isolierte Vorschau
um, SJ-3B.2a das rein flüchtige Planmodell und SJ-3B.2b dessen individuelle
Qt-Bearbeitung im vorhandenen Dialog. Der minimale Einstieg unter
`Einstellungen → Schuljahre` mit aktuellem Schuljahr, flüchtigen
Zieljahresangaben und Dialog ist integriert. SJ-3C.6 ergänzt die finale
Bestätigung sowie die verdrahtete Step-up-, Backup-, Maintenance- und
Transition-Ausführung; die manuelle macOS-Abnahme bleibt offen. Die folgende
Informations-, Interaktions- und Accessibility-Semantik bleibt verbindlich.

SJ-3B.1 zeigt den vorhandenen Preview-Kopf und jedes vorhandene Item genau
einmal in unveränderter Reihenfolge. Die Tabelle ist nicht editierbar und bei
kleinem Fenster horizontal und vertikal scrollbar. `Ungelöst`, Zielstatus und
Warnungen sind sichtbarer Text mit Accessible Names beziehungsweise
Descriptions. Der Dialog besitzt ausschließlich `Schließen`.

SJ-3B.2b ersetzt die vorgeschlagenen Zielspalten durch einzeln fokussierbare
Auswahlfelder je Kind. Zielstatus, Zielstammgruppe und Zielkurs zeigen immer
den aktuellen flüchtigen Planstand. Das Öffnen eines Auswahlfelds, Fokus oder
Tab-Navigation trifft keine Entscheidung; erst die bewusste Aktivierung einer
benannten Option erzeugt eine neue Planinstanz. Ausgeschiedene Kinder zeigen
weder Zielgruppe noch Zielkurs. Ursprüngliche Hinweise und aktuelle Blocker
bleiben textlich unterscheidbar. Es gibt weder Checkboxen noch
Mehrfachauswahl, Sammelaktion oder Ausführungsschaltfläche.

Der Einstieg lautet `Einstellungen → Schuljahre`. Der fachliche Ablauf enthält
weiterhin zehn Phasen:

1. Neues Schuljahr festlegen.
2. Sicherheitsprüfung und Backup.
3. Vorschlag erzeugen.
4. Vollständige Kindliste.
5. Sonderfälle bearbeiten.
6. Validierung ohne Schreiben.
7. Zusammenfassung.
8. Passwort und explizite Bestätigung.
9. Atomare Ausführung.
10. Ergebnis.

Die integrierte Oberfläche verdichtet diese fachlichen Phasen ohne neue
Wizard-Domainlogik in zwei sichtbare Präsentationsschritte. `Zuordnungen
prüfen` enthält Orientierung, Filter, Kindliste, Einzel- und
Sammelbearbeitung. `Prüfen und aktivieren` enthält die vollständige
Zusammenfassung, Prüfcheckbox, Passwort, finale Aktion und das vorhandene
Ausführungsfeedback. Vor Beginn der atomaren Ausführung kann zwischen beiden
Schritten gewechselt werden; dieser UI-Zustand schreibt nichts und verändert
den Plan nicht.

Die Phasenanzeige unterscheidet `aktuell`, `geprüft` und `blockiert` textlich;
Farbe unterstützt nur. Ein späterer Schritt darf keine noch offene
Entscheidung verdecken. Zurücknavigation vor der atomaren Ausführung bleibt
möglich und verändert nur den flüchtigen Plan. Während der kritischen
Ausführung ist Schließen blockiert; es werden keine erfundenen Prozentwerte
gezeigt.

Die dominante Arbeitsfläche ist die Kindliste mit den Spalten
Kind, bisheriges Schuljahr, bisherige Stammgruppe, bisheriger Kurs, neues
Schuljahr, neue Stammgruppe, neuer Kurs, Zielstatus und Warnungen. Der Dialog
startet mit `Nur ungelöst`; `Alle Kinder` stellt die vollständige Planreihenfolge
jederzeit wieder her. Zusätzliche Kurs- und Stammgruppenfilter bleiben bis zur
bewussten Anforderung eingeklappt. Ein klarer Ergebnistext nennt weiterhin
Gesamtzahl, sichtbare Zahl und Zahl ungelöster Kinder. Es gibt keine
automatisch entfernten Planitems oder allein durch Sortierung behauptete
Priorität. Die Tabelle bleibt read-only; eine ausgewählte Zeile steuert die
persistent außerhalb der Tabelle liegenden, accessibility-sicheren
Einzelentscheidungen.

Mehrfachauswahl unterstützt die bewusste Sammeländerung von Zielkurs und
Zielstammgruppe. Die Aktion benennt Anzahl und Ziel vor der Übernahme in den
flüchtigen Plan. Ohne sichtbare Auswahl bleiben die Sammelaktionen vollständig
ausgeblendet; Auswahlzähler, `Alle sichtbaren auswählen` und `Auswahl aufheben`
bleiben als ruhige Vorbereitung sichtbar. Stammgruppe bleibt ohne
ausdrückliche Änderung unverändert. Individuelle Änderungen bleiben danach
sichtbar. Kursfarben dürfen wie bisher organisatorisch unterstützen, aber
weder Fortschreibung, Gültigkeit, Warnung noch Leistung ausdrücken.

Stufe 3 wird immer mit `Ungelöst` vorgeschlagen und benötigt eine bewusste
Auswahl aus `Ausgeschieden`, `Verbleibt in <Kurs>`, einem vorhandenen Zielkurs
oder `Ungelöst`. Das Kursfeld enthält ausschließlich Kursnamen sowie
`Verbleibt in <Kurs>` statt technischer Entscheidungsformulierungen; nach der
Auswahl bleibt der konkrete Kursname im als `Zielkurs` bezeichneten Feld
sichtbar und wird nicht zusätzlich als wählbare Option wiederholt.
Bei einem ungelösten Kurs-3-Fall erscheint der aktuelle Kurs ausschließlich
als `Verbleibt in <Kurs>` und nicht zusätzlich als generische Kursoption.
`Ausgeschieden` und `Ungelöst` stehen getrennt als sekundäre Statusaktionen bereit.
Die Zielstammgruppe folgt demselben Muster: Das Feld zeigt die aktuelle Wahl,
die Optionsliste ausschließlich andere Gruppennamen ohne technische Präfixe.
Der Zielstatus nennt bei einem Stufenwechsel die tatsächliche Richtung, etwa
`Wechsel 1 → 3` oder `Wechsel 3 → 2`; identischer Kurs und Kurswechsel
innerhalb derselben Stufe bleiben davon eindeutig unterschieden.
`Ausgeschieden` wird verständlich als Ende der aktuellen
Einschreibung erklärt und niemals als Archivierung oder Löschung bezeichnet.

Validierungsfehler erscheinen in einer zusammenfassenden `InlineMessage` und
direkt textlich an der betroffenen Zeile. Nach Validierung erhält der erste
Blocker Fokus; `Nur ungelöst` ist als nächste ruhige Aktion erreichbar.
Warnungen, Auswahl, bearbeitete Werte und Zielstatus dürfen nie ausschließlich
durch Farbe, Icon, Position oder Tooltip vermittelt werden.

Die Zusammenfassung nennt mindestens Ausgangs- und Zielschuljahr, Zahl aller
Kinder, fortgeschriebene Kurse, Wiederholungen, andere Kursziele,
Stammgruppenänderungen, Austritte und verbleibende Blocker. Backupstatus,
Quellenfrische und Rückdatierungsprüfung werden in verständlicher Sprache
gezeigt; Hashes, lokale Pfade und technische Tokens bleiben außerhalb der
normalen Oberfläche.

Im Arbeitsbereich zeigen fünf kompakte Kennzahlen ausschließlich Wechsel
1→2, Wechsel 2→3, ungelöst, ausgeschieden und Stammgruppenänderungen. Die
vollständige Zusammenfassung steht im getrennten letzten Schritt. Unterhalb
von 900 Pixeln Breite werden Kindliste und externe Einzelbearbeitung
untereinander angeordnet; der Arbeitsbereich ist vertikal scrollbar und
erzeugt keinen horizontalen Gesamtscroll. Bei sehr geringer Höhe kann die
kompakte Kennzahlenkarte entfallen, weil dieselben Werte im Abschluss
vollständig erreichbar bleiben.

Die finale Schutzstufe besitzt ein sensitives Passwortfeld mit eindeutigem
Accessible Name, bestehender Drosselung und generischer Fehlermeldung. Die
nicht vorbelegte Bestätigung lautet `Ich habe alle Zuordnungen geprüft.`. Die
Primäraktion benennt das konkrete Ziel, beispielsweise
`Schuljahr 2026/27 verbindlich aktivieren`. Touch ID beziehungsweise
Gerätecredential erscheint in der ersten Freigabe nicht als Alternative.
Escape oder Schließen bricht vor Beginn der atomaren Ausführung ohne Schreiben
ab; Enter löst die irreversible Primäraktion nicht aus einem Tabelleneditor,
Passwortfeld oder Bestätigungskästchen beiläufig aus.

### Tastatur und Accessibility

- Die Schrittfolge, Filter, Tabelle, Mehrfachauswahl, Sammelaktionen,
  Einzelbearbeitung, Validierung, Zusammenfassung, Passwort, Bestätigung und
  Primäraktion liegen in einer nachvollziehbaren Tab-Reihenfolge.
- Die Filter liegen ohne ein irreführendes Suchkürzel in der sichtbaren
  Tab-Reihenfolge. Escape setzt zuerst einen abweichenden Filter zurück und
  bricht danach nur gemäß sicherem Dialogvertrag ab.
- Tabellenzeilen und editierbare Zellen sind per Tastatur erreichbar.
  Pfeiltasten navigieren innerhalb der Tabelle; Leertaste schaltet eine
  fokussierte Auswahl, Enter öffnet die eindeutige Zeilenbearbeitung.
- Mehrfachauswahl und Bulk-Aktionen nennen im Accessible Name die ausgewählte
  Kinderzahl. Fokus kehrt nach einer Sammeländerung sinnvoll in die Liste
  zurück.
- Jede Zeile besitzt eine zugängliche Gesamtbeschreibung mit Kind, bisherigem
  und neuem Kontext, Zielstatus und Warnungen. Spaltenheader bleiben für
  Screenreader zugeordnet.
- Status, Warnung, Auswahl und Fehler besitzen sichtbaren Text sowie
  Accessible Name beziehungsweise Description; keine Information ist nur
  farblich oder nur im Tooltip verfügbar.
- Die vollständige Kindliste bleibt bei Vergrößerung und hoher Textskalierung
  bedienbar. Kopf, Validierungsstatus und notwendige Aktionen bleiben
  erreichbar; unvermeidbarer Tabellenscroll darf keinen horizontalen
  Gesamtscroll des Assistenten erzeugen.
- Der Ergebniszustand erhält Fokus und nennt Erfolg oder sanitisierten Fehler,
  Ergebniszahlen und den sicheren nächsten Schritt. Technische
  Operation-Token, Hashes und Pfade werden nicht vorgelesen.

Vor Produktfreigabe sind Tastaturlauf, hohe Textskalierung, sichtbarer Fokus,
Kontrast, Screenreader-/VoiceOver-Ausgabe, Fehlerfokus und reale Bedienung des
vollständigen Assistenten separat abzunehmen. Automatisierte Qt-Tests ersetzen
diese reale Accessibility- und UX-Prüfung nicht.

## Intern gegatete LEG- und Bericht-HTML-Hosts - visuelle Grenze

Der intern gegatete LEG-HTML-Host übernimmt bestehende Grün-Kontextrollen,
Typografie, Karten, Radien, Abstände, Fokusrahmen und Buttonhierarchie des
freigegebenen Spikes. Zu jedem Zeitpunkt ist genau eine der sechs Phasen
sichtbar; Phasenwechsel verwenden ausschließlich DOM-State und keine Opacity-/
GraphicsEffect-Animation. Der Kompetenz-/Belegbereich wird beim ersten Öffnen
lazy aufgebaut und behält danach seinen DOM-Zustand. Verständliche Fehler
werden ohne technische IDs, Pfade, Hashes oder Exceptions am Host angezeigt.
Die intern gegatete HTML-Berichtswerkstatt übernimmt die vorhandenen ruhigen
Bericht-Kontextrollen, Typografie, Karten, Radien, Abstände, Fokusrahmen und
Buttonhierarchie. Genau eine der fünf Hauptseiten `Schreiben`, `Fachbereiche`,
`Kompetenzen & Belege`, `Vorschau` und `Revisionen` ist sichtbar; Navigation
bleibt DOM-lokal und ohne Opacity-/GraphicsEffect-Animation. Der responsive
Berichtskopf ordnet Kind, Stammgruppe, Berichtstyp, Zeitraum, verantwortliche
Lehrkraft und Draft-/Finalisierungsstatus ohne Überlagerung. Kompetenzen und
Belege werden lazy aufgebaut. Die Vorschau nennt ihre Draftquelle sichtbar;
Revisionen bleiben ruhige read-only Karten. Diese Konkretisierung begründet
kein Redesign und keine allgemeine Freigabe der CSS-Werte als neues
Produkt-Designsystem.

## Phase 2 Berichte-Übersicht - neutrale Belegdarstellung

**Status:** lokal implementiert und automatisiert im Qt-Offscreen-Modus
geprüft. Reale macOS-Trackpad- und VoiceOver-Abnahme bleiben offen.

Die Timeline zeigt ausschließlich vorhandene Dokumentationsereignisse im
aktuellen Schuljahr. Sie wird als horizontal scrollbare Liste
gerendert und startet beim Öffnen am neuesten Ende. Abhängig von der
verfügbaren Breite sind ungefähr zwei, vier oder fünf Ereigniskarten
gleichzeitig sichtbar. Diese Werte beschreiben ausschließlich den Viewport und
sind weder Inhaltsgrenze noch Auswahlgröße oder Begrenzung der
Ereignisprojektion. Ältere enthaltene Ereignisse bleiben durch bewusstes
horizontales Scrollen erreichbar. Automatisches Karussell und automatische
Bewegung sind unzulässig.

Die vollständige gelieferte Liste besitzt grundsätzlich den Zielumfang 15;
alle gültigen Bericht-/LEG-Abschlussereignisse bleiben auch bei mehr als 15
Einträgen sichtbar. Das Widget entfernt, priorisiert oder sortiert keine
Ereignisse. Jedes Ereignis trägt ein vollständiges Datum, einen sachlichen
Ereignistyp und nur vorhandenen neutralen Kontext. Bericht und LEG bleiben als
Dokumenttypen erkennbar.

Die sichtbare Timeline verwendet die ruhige verbundene Meilensteinachse der
vorherigen Berichte-Übersicht: ein kompakter runder Ereignismarker je
geliefertem Ereignis, vollständiges Datum sowie zentrierter Titel und
vorhandener Kontext. Große voneinander getrennte Inhaltskarten sind für diesen
Bereich nicht vorgesehen. Die Achse ist ausschließlich Formsprache; sie
verbindet keine fachlichen Entwicklungsstufen und erzeugt keine
Verlaufsinterpretation.

Der Berichtsbereich unterstützt die Auswahl vorhandener Belege für einen
Bericht. Er ist keine zusätzliche Lernentwicklungsdarstellung und dupliziert
weder den Profilbereich `Überblick` noch die Detailansicht `Kompetenzen`.
Eine Beobachtung, ein Berichtaggregat und ein LEG-Aggregat erscheinen jeweils
höchstens einmal. Kompetenzzuordnungen und technische Revisionen erscheinen
nicht als eigene Karten.

Die Timeline ist über Trackpad, horizontale Scrollbar, sichtbare Links-/Rechts-
steuerung und Tastatur bedienbar. Scrollfläche und Steuerungen besitzen
verständliche Accessible Names und sichtbaren Fokus. Shift+Mausrad darf nur
bei stabiler technischer Umsetzung horizontal scrollen; normales vertikales
Scrollen blockiert die äußere Profilscrollfläche nicht. Bei Resize bleibt die
Position möglichst erhalten und ein zuvor erreichtes neuestes Ende bleibt am
Ende. Bei Refresh dient eine stabile Ereignisidentität als Anker. Es gibt kein
automatisches Nachscrollen.

Der feste Abschnitt `Überfachliche Entwicklung` zeigt zuerst genau zwei Karten:
`Selbst- und Sozialkompetenz` und `Arbeits-/Lernkompetenz`. Diese Karten sind
unabhängig von der individuellen Fachauswahl sichtbar. Darunter zeigt der
Abschnitt `Fächer` ausschließlich die individuell effektiven
Unterrichtsfächer. Alle Karten zeigen absolute Dokumentationsmengen. Der
Phase-2-Balken besteht
aus genau einem gleich breiten neutralen Segment je dokumentierter aktueller
Kompetenz im aktuellen Schuljahr und erscheint ausschließlich für ein über
`effective_documentation_subjects(student_id, school_year_id)` relevantes
Unterrichtsfach oder für eine der beiden festen überfachlichen Domänen. Es gibt
keine ungefüllte Restspur, keinen
fachbezogenen oder gemeinsamen Nenner, keine Normalisierung, Schwelle,
Ampelstufe, Qualitätsfarbe, Prozentangabe oder Animation. Viele Segmente dürfen
ruhig umbrechen; sie werden nicht abgeschnitten oder zu einer Qualitätsstufe
verdichtet. Bei null bleibt nur der neutrale absolute Text sichtbar. Die
Bewertungsfarben `--` bis `++` sind für diese Darstellung unzulässig.

Da die Fachkarte kein Diagramm mehr zeigt, erhält sie ein kleines
fachspezifisches Textsymbol. Das Symbol ist eine ruhige Orientierungshilfe,
kein Logo, kein Datenwert und keine Bewertung. Es wird ausschließlich aus der
vorhandenen `subject_id` gewählt; für unbekannte Fächer erscheint ein neutraler
Punkt. Fachname, Zählertexte und Accessible Name tragen die Bedeutung
unabhängig vom Symbol.

Fachkarten bleiben in der bestehenden neutralen kanonischen Fachreihenfolge.
Sie werden weder nach Beobachtungs- oder Kompetenzanzahl, Bestätigungsstand,
Aktualität, Rating, vermeintlicher Wichtigkeit noch nach einer anderen
Dokumentationsmenge umsortiert. Mehr Dokumentation verändert weder die
Position einer Fachkarte noch ihre visuelle Gewichtung.

Die erlaubte Sprache beschreibt ausschließlich Vorhandenes, beispielsweise
`Beobachtung dokumentiert`, `Kompetenz dokumentiert`,
`Kompetenz bestätigt`, `<n> Kompetenzen dokumentiert`,
`<n> Beobachtungen im aktuellen Schuljahr`, eine nur bei vorhandenem Stand
sichtbare neutrale Bestätigungsinformation, `Belege ansehen` und
`aktuell bestätigter Stand vorhanden`. Der zugängliche Text nennt dieselben
absoluten Mengen und beschreibt Länge oder Fläche nie als Status, Niveau oder
Bewertung.

Unzulässig sind x/y- und Prozentsemantik, Soll- oder Restmengen,
Fortschritt, Verbesserung, Verschlechterung, Entwicklungskurve,
Trendpfeil, Vorher-/Nachher-Vergleich, Stärke, Schwerpunkt, Defizit,
Förderbedarf, Empfehlung, Priorität, Wichtigkeit, Auffälligkeit, Rangfolge
oder Formulierungen wie `wenig dokumentiert` und `viel dokumentiert`.
Fehlende Dokumentation wird weder hervorgehoben noch als
Handlungsaufforderung formuliert.

Historische Kompetenzen erscheinen nicht in aktuellen Zählern oder Segmenten.
Schnellbeobachtungen erhalten ohne vorhandene Kompetenzzuordnung keine
Kompetenzdarstellung. Der sichtbare aktuelle Bestätigungsstand enthält weder
Rating noch rekonstruierte Historie, Abschluss- oder Zielerreichungsdeutung.

## P1-Paket 1 - vorsichtige Bestätigungsdarstellung

Ein historisch nicht beweisbar geordneter Bestätigungsstand verwendet keine
positive oder warnende Ja-/Nein-Ampel. Profil, Cockpit, Bericht und LEG zeigen
ruhig und textlich eindeutig:

`Bestätigungsstand unklar – bitte erneut bestätigen`

Die vorhandene Bestätigungsaktion bleibt der einzige Auflösungsweg. Der
unklare Zustand darf nicht als `Bestätigter Stand` gezählt und nicht als
sicher `Neuere Beobachtungen` formuliert werden. Technische Sequenzen,
Zeitstempel, Operation-Token, Journal- oder Recoveryzustände bleiben unsichtbar.

## Sprint 0.2S.1 - Ruhiger Support-Assistent

Der eigenständige Support-Assistent verwendet einen linearen Schrittfluss mit
genau einer dominanten Primäraktion: zuerst `Reset-Anfrage öffnen`, nach
vollständiger Prüfung `Reset-Code erzeugen`. Es gibt keine automatische Suche,
kein Dashboard und keine Produktnavigation. Helle ruhige Karten trennen
Anfrage, flüchtige Installationsbezeichnung und öffentlichen Schlüsselstatus.

Gültigkeit wird mit sichtbarem Text `Gültig` und einem positiven, nicht allein
farblichen Status dargestellt. Ablehnungen erscheinen als sachliche
Inline-Meldung ohne Payload-, Signatur- oder Pfaddetails. Der Fingerprint wird
gekürzt, technische IDs nur soweit für die Zuordnung erforderlich. Der
Ergebniszustand zeigt Ablaufzeit sowie die ausdrücklich ausgelösten Aktionen
`Kopieren` und `Datei speichern`; der Token selbst wird nicht dauerhaft im
Layout gezeigt.

Der Starttext lautet verbindlich: `Dieses Werkzeug erzeugt keinen Zugang und
kein Passwort. Es erstellt ausschließlich einen zeitlich begrenzten
Reset-Code.` Tastaturfokus folgt dem linearen Ablauf; alle Datei-, Passphrase-
und Hauptaktionen besitzen Accessible Names. Die App ist visuell und im
Fenstertitel eindeutig vom Jenaplan-Kompetenzmanager getrennt.

## Sprint 0.2U.2 - Update- und Pilot-Handoff

`Einstellungen > Updates` folgt der bestehenden ruhigen Übersichts-/Unterseiten-
struktur. Genau eine blaue Primäraktion `Nach Updates suchen` öffnet das native
Sparkle-Fenster; Versionsdaten, Kanal, letzter Prüfzeitpunkt und Fallback-Hinweis
bleiben kompakte Klartextprojektionen. Kryptografische Details, URLs und lokale
Pfade erscheinen nicht in der normalen Nutzeroberfläche.

Der Pilot-Zusatzschritt der `Ersten Schritte` verwendet genau eine bewusste
Aktion zum vorhandenen Restore-Weg. `Später über Einstellungen` bleibt der
ruhige Abschluss; Escape importiert nichts. Der Text kennzeichnet synthetische
Beispieldaten und die ersetzende Wirkung des fachlichen Restore eindeutig.

## Sprint 0.2B.6 - Support-Terminalführung

Die externe `.command` verwendet eine lineare deutsche Terminalführung ohne
Menüvermischung von Reset und Schlüsselanlage. Hinweise sind sachlich,
Entscheidungen explizit und Exitcodes sichtbar. Anfrageübersicht zeigt nur
technische Werte; Passphrase bleibt unsichtbar. Genau eine bewusste `JA`-
Bestätigung bindet die Geräteherkunft, eine weitere optionale `JA`-Bestätigung
steuert allein die Tokenanzeige. Abbruchtexte enthalten keine Exceptiondetails,
Secrets, vollständigen Private-Key-Inhalt oder ungefragt gespeicherte Werte.

Die Finder-Starter halten das Terminal bis zu einer Eingabetaste offen, lesen
aber selbst weder Passphrase noch Anfrage oder Token. Reset und
Schlüsselbereitstellung bleiben zwei klar benannte `.command`-Dateien.

## Brand Color Harmonization - App-Icon und Arbeitskontexte

Die zentrale Markenpalette leitet sich kontrolliert aus dem App-Icon ab. `Brand
Navy` traegt Struktur, wichtige Texte, dunkle Icons und die Sidebar. `Brand
Blue` traegt Primaeraktionen und zentrale Auswahl. `Brand Teal` traegt Fokus,
neutrale Dokumentationsinformation und den Beobachtungskontext. `Brand Green`
traegt ausschliesslich den LEG-Arbeitskontext und kleine unterstuetzende
Markenakzente. `Brand Lime` bleibt ein sehr sparsamer dekorativer Akzent.
`Brand Orange` traegt den Berichtskontext und offene Dokumentationspunkte, aber
keinen Fehlerzustand. Sehr helle Blue-, Teal-, Green-, Lime-, Orange- und
Neutral-Surfaces sind nur fuer kleine Kontext-, Icon- und Auswahlflaechen
zulaessig; grosse Arbeitsflaechen bleiben neutral und opak.

`DialogHeader` verwendet die wiederverwendbaren Kontextrollen `observation`,
`report`, `learning_conference` und `neutral`. Beobachtung wird durch Teal, LEG
durch Green und Bericht durch Orange unterschieden. Die Rolle darf nur in
Iconflaeche, duenne Akzentlinie, sehr heller Kopfflaeche, lokaler aktiver
Navigation oder kleinen Kontextdetails erscheinen. Berichtswerkstatt und LEG
verwenden fuer ihre lokale aktive Navigation die zentrale helle
Blue-Auswahlflaeche und Brand Blue als Marker; der Beobachtungskontext behaelt
seine Teal-Auswahlflaeche innerhalb desselben Strukturmusters. Hover bleibt
neutral und der globale Fokusrahmen Brand Teal. Die Kontextrolle bezeichnet weder
Status noch Bewertung, Leistung, Prioritaet, Erfolg oder Fehler. Titel, Icon und
sichtbarer Kontext tragen die Bedeutung auch ohne Farbe. Kleine CRUD-,
Stammdaten-, Stundenplan-, Schueler- und App-Info-Dialoge bleiben neutral.

Kursfarben, Bewertungsfarben `--` bis `++`, neutrale
Dokumentationsabdeckung und Feedbackfarben bleiben technisch und visuell
getrennte Systeme. Keine Marken- oder Dialogfarbe ersetzt eines dieser Systeme.
Dokumentvorschauen, finale Revisionen, Tabellen, Editoren und vollstaendige
Inhaltskarten bleiben neutral beziehungsweise papierartig.

Die Sidebar nutzt einen ruhigen Navy-Blau-Teal-Verlauf mit genau einem hellen
Teal-Auswahlmarker. Primaerbuttons verwenden Brand Blue, Sekundaerbuttons helle
Blue-/Teal-Surfaces und Quiet-Buttons Markenfarbe nur bei Hover oder Fokus. Der
globale Fokus ist Brand Teal und bleibt als sichtbarer Rahmen erhalten. Glas
bleibt auf Sidebar, Navigation, Suche, Filter, Menues, Tooltips und kleine
Overlays begrenzt; Dialogkontextflaechen sind hell und opak. Es entstehen keine
neuen Motion-Typen.

Kontrastvertrag auf Weiss: Brand Navy `10,87:1`, Brand Blue `5,37:1`, Brand
Teal `4,80:1`, Brand Green `4,92:1`, Brand Orange `5,08:1`. Brand Navy erreicht
auf allen hellen Kontext-Surfaces mindestens `9,76:1`. Farbe ist niemals der
einzige Informationstraeger; Accessible Names, Fokusreihenfolge und vorhandene
Tastaturablaeufe bleiben verbindlich.

## Version 0.2.0 - Arbeitsfenster und Bestätigungsdialoge

Beobachtung, Bericht und LEG öffnen als maximierte normale Fenster auf dem
Bildschirm des Hauptfensters. Sie verwenden die verfügbare Geometrie mit
Menüleiste und Dock, niemals den macOS-Vollbildmodus mit eigenem Space.
Vorhandene Scrollflächen bleiben die Absicherung für kleine Displays; kein
Arbeitsfenster darf außerhalb der sichtbaren Geometrie beginnen.

Bestätigungsbuttons zeigen ihren vollständigen Text ohne Eliding oder
Abschneiden. Die Breite wird nach der finalen Schriftmetrik mit Reserve für
Innenabstand und sichtbaren Fokusrahmen bestimmt. Zwischen Aktionen bleiben
mindestens zwölf Pixel. Der sichere Fortsetzungsweg ist die blaue Primäraktion;
Escape und Enter lösen keine verwerfende oder überspringende Sekundäraktion aus.

Im LEG ist genau ein Inhaltsanker sichtbar und interaktiv. Nicht aktive Seiten
bleiben für den Erhalt ungespeicherter Eingaben im Seitencontainer, werden aber
aus Darstellung, Maus- und Tastaturinteraktion genommen. Animationen dürfen
keinen Effekt auf dem gesamten Seitenstack hinterlassen.

## Version 0.2.0 - Release-Dokumente und Screenshots

Release-PDFs verwenden weiterhin die bestehende blau-graue Typografie,
Seitenköpfe, Fußzeilen und A4-Raster des registrierten Dokumentbuilds.
Release-Screenshots werden in 1180 × 760 und 1400 × 900 erzeugt, zeigen
vollständige ruhige Zustände ohne abgeschnittene Primäraktionen und enthalten
keine echten Daten, Geheimnisse oder Pfade.

Sicherheitskommunikation bleibt sachlich: Touch ID ist optional, das Passwort
bleibt Fallback, die automatische Sperre bleibt aktiv und die App-Sperre wird
nicht als Verschlüsselung dargestellt. Ad-hoc-Signierung und offene reale
Abnahmen dürfen visuell oder textlich nicht in eine Freigabe umgedeutet werden.

## Support-Reset - Sprint 0.2B.5

Der Support-Reset ist ein ruhiger modaler Recoveryprozess, keine neue
Hauptnavigation. Das Auth-Gate verwendet den dezenten sekundären Einstieg
`Weitere Wiederherstellungsmöglichkeiten`; die Sicherheits-Unterseite erhält
unter `Wiederherstellung` eine sekundäre Anfrageaktion.

Jeder Zustand zeigt genau eine eindeutige blaue Primäraktion. Anfragewerte und
Exporttext stehen in gut lesbaren, umbruchfähigen Flächen ohne horizontale
Scrollbalken. Kopieren, Speichern und Import sind explizite sekundäre Aktionen.
Token wird nur im Eingabeschritt angezeigt und verschwindet vor der Vorschau.

Die irreversible Aktion heißt vollständig `Sicherheitsbackup erstellen und
Passwort zurücksetzen`. Warnung entsteht durch klare Folgen und Abstand, nicht
durch aggressive rote Flächen. Escape/Schließen bricht nur vor dem Worker ab;
während Backup und Commit blockiert der Dialog das Schließen und zeigt einen
unbestimmten Fortschritt ohne erfundene Prozentwerte.

Generische Ablehnung lautet: `Der Reset-Code ist ungültig, abgelaufen oder passt
nicht zu dieser Installation.` Eine leere Registry verwendet den verbindlichen
Nichtfreigabe-Hinweis. Layout, Fokus, Tastatur und opake Sperrung bleiben bei
1180 x 760 und 1400 x 900 vollständig nutzbar.

Der Einstieg erklärt knapp, dass die geschützte lokale Dateninstallation
vollständig verfügbar sein muss. Ein blockierter Final-V4-Preflight lautet
neutral: `Die geschützten lokalen Daten konnten nicht vollständig geprüft
werden. Das Passwort wurde nicht zurückgesetzt.` Ein Backupfehler benennt klar,
dass das Sicherheitsbackup nicht erstellt und geprüft werden konnte und deshalb
nichts zurückgesetzt wurde. DMK-, Key-ID-, Pfad-, Hash- und Stacktracedetails
bleiben unsichtbar.

Kann die laufende Runtime nach einem Fehler nicht sicher fortgesetzt oder der
atomare Security-Commit nicht eindeutig als vorher beziehungsweise nachher
bewiesen werden, lautet der Abschluss neutral: `Der Sicherheitszustand konnte
nicht eindeutig bestätigt werden. Die App wird beendet und prüft ihn beim
nächsten Start.` Danach gibt es keine Rückkehr in die laufende Fachoberfläche;
der nächste Startup löst ausschließlich den autoritativen Security Store auf.

## Geräteanmeldung und Touch ID - Sprint 0.2B.4a

Der bestehende Passwortbereich bleibt die dominante, immer verfügbare
Fallback-Fläche. `Mit Touch ID entsperren` ist eine klar benannte sekundäre
Aktion und erscheint nur bei tatsächlich verfügbarer, eingerichteter lokaler
Biometrie und konsistentem Gerätecredential. Ein Abbruch zeigt ruhig den
Passwortpfad und startet keinen automatischen Dialogloop.

`Einstellungen > Sicherheit` erhält im bestehenden Bereich
`Komfort beim Entsperren` zwei ruhige Schalterzeilen und eine sekundäre
Widerrufsaktion. Direkt unter `Auf diesem Gerät angemeldet bleiben` steht:
„Die App wird weiterhin nach Inaktivität oder Ruhezustand gesperrt.“ Touch ID
ist nur bei aktivem Gerätecredential sichtbar. Technische Begriffe wie
Keychain, Token, Hash, Salt oder Epoch stehen nicht im Primärtext.

Die Statussprache unterscheidet `verfügbar`, `nicht eingerichtet`,
`nicht verfügbar` und `aktiviert` ohne Alarmfarbe. Es gibt genau eine dominante
Aktion je Zustand, keine neue Hauptnavigation, keine eigene Unterseite und keine
Behauptung von Datei- oder Secure-Enclave-Verschlüsselung. Login und Sperre
bleiben opak, bei 1180 x 760 und 1400 x 900 ohne verdeckte Passwortaktion.

## Erste Schritte - Sprint 0.2C.1

`Erste Schritte` ist eine ruhige Shell-interne Orientierungsansicht, keine
Tour mit Overlays und keine Popup-Kette. Sie nutzt `PageHeader`, eine
grosszuegige Hauptflaeche, kurze Plain-Text-Abschnitte, wenige Stichpunkte und
zentrale Buttonrollen. Der Primaerbutton bleibt blau und heisst je nach Schritt
`Weiter` oder im letzten Schritt `Erste Schritte abschließen`; `Zurück` und Zielnavigation bleiben sekundaer,
`Erste Schritte überspringen` bleibt ruhig.

Die Ansicht ist bei 1180 x 760 und 1400 x 900 bedienbar, verwendet keinen
horizontalen Gesamtscroll und legt keinen fachlichen Inhalt unter transparente
Overlays. Statuszeilen sind textlich eindeutig (`Bereits eingerichtet`,
`Noch offen`, `Nicht geprüft`) und nie reine Farbkommunikation. Beim Backup
bedeutet `Sicherungsdatei gefunden – bitte prüfen` ausdrücklich nur einen
Dateifund, keine Integritäts- oder Wiederherstellungsprüfung. Enter aktiviert
die Primaeraktion; Escape ueberspringt nicht unbemerkt, sondern bewirkt keinen
Abschluss. Die Rueckkehrzeile `Zurück zu Erste Schritte` erscheint nur nach
einem bewussten Navigationssprung aus dem Onboarding.

Der Final-V4-Pilotflow besitzt exakt fünf kurze Schritte. Statuszeilen nennen
Stammgruppe, Kurs, Schüler, Stundenplan oder Backup nur neutral und blockieren
niemals. Die globale Dokumentationsfachauswahl ist kein Schritt und kein
Status. Sicherheitscopy erklärt lokale Verschlüsselung und Recovery-Codes
verständlich; Support Reset bleibt ein unauffälliger betreuter Ausnahmehinweis.

## Authentifizierung und Sperre - Sprint 0.2B.4

Die minimale Authentifizierungsoberflaeche ist eine ruhige, vollstaendig opake
Einzelflaeche ohne fachlichen Hintergrund. Sie zeigt nur App-Identitaet,
aktuellen Schritt, ein grosszuegiges Passwort- beziehungsweise Recovery-Feld,
eine generische Inline-Rueckmeldung und genau eine blaue Primaeraktion. Enter
loest die Primaeraktion aus. Passwortfelder erlauben Einfuegen und besitzen
eine explizite Anzeigen-/Verbergen-Aktion; automatische Zwischenablage oder
Dateiablage ist ausgeschlossen.

Recovery-Codes werden einmalig in einer gut lesbaren Monospace-Flaeche mit
ausreichendem Zeilenabstand und druckfreundlichem Kontrast gezeigt. Die
Sicherungsbestaetigung steht direkt vor dem Abschlussbutton und ist nicht
vorbelegt. Sprache bleibt ruhig und erklaerend, auch bei Drosselung oder
fail-closed Fehlern.

Die Einstellungsuebersicht bleibt das bestehende Muster aus einer aktiven
Unterseite; `Sicherheit` wird als vierte Navigationskarte aufgenommen. Die
Unterseite zeigt Passwortschutz, feste Sperrzeitwahl 5/10/15/30/60,
Passwortwechsel, Recovery-Code-Erneuerung und `Jetzt sperren`. Im aktuellen
Final-V4-Produktstand trennt der Hinweis den Zugangsschutz von der zusätzlichen
Verschlüsselung der Fachdaten, verwalteten Dokumente und Backups. Ein kurzer
FileVault-Hinweis ergaenzt ihn. Interne Schlüsselbegriffe werden nicht
angezeigt.

Die Sperransicht ist niemals transparent. Beim Sperren verschwinden Shell,
Dialoge, Popups, Namen und alle fachlichen Inhalte vollstaendig aus der
sichtbaren Fensterliste; die neutrale Sperransicht besitzt denselben opaken
Hintergrund bei 1180 x 760 und 1400 x 900. Ungespeicherte Eingaben bleiben im
verdeckten Widgetbaum erhalten und erscheinen nach Entsperren unveraendert.

## Einstellungsnavigation - Sprint 0.2A.4

Einstellungen sind keine Dashboard-Fläche. Die Übersicht verwendet vier grosse ruhige `SettingsNavigationCard`-Zeilen mit Titel, kurzer Erklärung, Status und Chevron. Die ganze Karte besitzt vorhandene interaktive Card-Zustände und reagiert auf Enter und Leertaste. Eine Unterseite zeigt einen sichtbaren ruhigen Zurück-Mechanismus; Akkordeons, dichte Formularoptik und parallele Bearbeitungsbereiche sind ausgeschlossen. Die Datensicherungsseite nutzt einen blauen Primärbutton nur für `Backup erstellen` beziehungsweise nach ausdrücklicher Warnung `Wiederherstellung starten`; Prüfung und Vorbereitung bleiben neutral.

Lange Datensicherungsoperationen zeigen eine textlich eindeutige Phase und einen unbestimmten Progress-Indikator. Prozentwerte sind nur mit einem echten Core-Fortschrittsvertrag zulaessig und werden hier nicht simuliert. Waehrend `running` und `finishing` sind Backup-, Restore-, Zurueck- und Hauptnavigation deaktiviert. Es gibt keinen Abbrechen-Button; ein Close-Versuch erklaert ruhig, dass der sichere Abschluss abgewartet wird.

Nach der Restore-Bestaetigung verschwindet die App erst, wenn der separate
Worker die authentisierte Uebernahme bestaetigt hat. Fehlt diese Bestaetigung,
bleibt die bestehende opake Hauptoberflaeche sichtbar und zeigt den ruhigen
Inline-Fehler `Die Wiederherstellung konnte nicht sicher gestartet werden. Die
App bleibt geöffnet; der lokale Datenbestand wurde nicht ersetzt.` Ein leeres
Restfenster oder ein Schliessen auf blossen Prozess-PID-Erhalt ist unzulaessig.

## Visual Signature und Release Polish - Premium UI Sprint 4

Die finale visuelle Signatur entsteht in der bestehenden Product Shell: ein sehr ruhiger blau-grauer Hintergrundverlauf trennt die Arbeitsflaeche von der tiefblauen, tonal abgestuften Sidebar. Aktive Navigation bleibt durch Flaeche, Text, linken Marker und sichtbaren Fokus eindeutig. Die Signatur fuehrt weder eine neue Navigation noch einen neuen Screen ein und bleibt bei allen freigegebenen Fenstergroessen stabil.

Glas bleibt ein Akzent fuer Sidebar, obere Navigationsflaechen, `SearchField`, `FilterBar`, Menues, Tooltips und kleine Overlays. Inhaltskarten, Tabellen, Formulare und Dokumentflaechen sind opak. Transparenz simuliert dort ausschliesslich leichte Tiefe vor dem Shell-Hintergrund; Blur, native Plattformtransparenz und grossflaechiges Glassmorphism bleiben ausgeschlossen.

Normale `AppCard`-Flaechen erhalten eine feine untere Tiefenkante statt eines starken Schattens. `soft` bleibt flach, `accent` darf als einziger Fokusbereich eine etwas deutlichere Surface-Hierarchie zeigen. Nur interaktive Karten besitzen eine kurze Hover-Elevation; sie bleibt layoutneutral, verwendet `MOTION_HOVER_MS` mit `OutCubic` und wird bei Reduced Motion unmittelbar in den Endzustand gesetzt. Vollflaechige Screen-Uebergaenge bleiben ausgeschlossen.

Dashboard-Hero, Schuelerprofilkopf, Berichtskontext und LEG-Kontext bleiben die vier bewusst hervorgehobenen Fokusbereiche. Sie werden nicht vergroessert und erhalten keine neue fachliche Farbsemantik; die nicht semantischen Dialog-Kontextrollen folgen dem Brand-Color-Vertrag. Tabellen, Listen, Header, Kontextmenues, Tooltips, Divider und Scrollbars verwenden denselben blau-grauen Kontrast- und Fokusvertrag. Das bestehende Outline-SVG-System behaelt die Rollen `16`, `20` und `24`; die unterschiedlichen Vordergrundfarben dienen ausschliesslich dem hellen Sidebar- beziehungsweise hellen Inhaltskontext.

QPainter wird nicht eingesetzt. Standardwidgets, zentrale QSS-Zustaende und das bestehende Motion-System liefern den benoetigten High-DPI-, Tastatur-, Fokus- und Reduced-Motion-Schutz. Die Release-Pruefung umfasst `1180 x 760`, `1280 x 800`, `1400 x 900` sowie Device Pixel Ratio 2.

## Fachfarben als read-only Orientierungsakzent

Fachfarben sind eine zentrale Design-System-Entscheidung und keine fachliche
Datenquelle. Die einzige produktive Matrix liegt als unveränderliche
`SUBJECT_ACCENT_COLORS`-Projektion in `src/desktop_app/theme.py`. Widgets
übergeben eine stabile kanonische `subject_id` an `subject_accent_icon` oder
`SubjectAccentMarker`; sie besitzen keine lokalen Hexwerte und leiten keine
Farbe aus sichtbarem Text ab.

| Fachkontext | Farbfamilie | Qt-Token / Wert |
|---|---|---|
| Deutsch | Rot | `SUBJECT_ACCENT_RED` / `#B3261E` |
| Mathematik | Blau | `SUBJECT_ACCENT_BLUE` / `BRAND_BLUE` (`#176BC1`) |
| Englisch | Schwarz | `SUBJECT_ACCENT_BLACK` / `COLOR_TEXT` (`#1F2937`) |
| Musik | Gelb | `SUBJECT_ACCENT_YELLOW` / `#D4A500`, dunkle Kontur `#6B5700` |
| Ethik | Orange | `SUBJECT_ACCENT_ORANGE` / `BRAND_ORANGE` (`#B2530A`) |
| Religion | Orange | `SUBJECT_ACCENT_ORANGE` / `BRAND_ORANGE` (`#B2530A`) |
| Schulgarten | Braun | `SUBJECT_ACCENT_BROWN` / `#795548` |

EPU beziehungsweise Sachkunde, Kreatives Gestalten sowie unbekannte oder nicht
eindeutig auflösbare historische Fächer verwenden sichtbar
`SUBJECT_ACCENT_NEUTRAL` (`#82909D`) mit dunkler Kontur. Es gibt keine
Hash-/ID-Zufallsfarbe. `Werken` wird nicht mit Kreativem Gestalten
gleichgesetzt. Die historisch diskutierten Namen `Werken` und `Projektplan`
werden nicht in die produktive Fachmatrix aufgenommen und erzeugen keine
Fachentität oder Aliasbeziehung. Der reservierte sehr helle Token
`SUBJECT_ACCENT_WHITE` darf bei einer späteren ausdrücklichen Freigabe nur mit
der vorhandenen dunklen Kontur erscheinen.

Selbst- und Sozialkompetenz sowie Arbeits-/Lernkompetenz sind überfachliche
Entwicklungs- und Beobachtungsbereiche, keine Unterrichtsfächer. In
Beobachtung, Cockpit, Bericht und LEG bleiben sie unter `Überfachliche
Entwicklung` mit neutralem Marker erreichbar; in der individuellen
Unterrichtsfachauswahl des Schülerprofils, im Stundenplan und in
Dashboard-Unterrichtskarten werden sie nicht als Unterrichtsfächer angeboten
oder dargestellt.

Der Fachname bleibt immer sichtbar und ist die semantische Hauptinformation.
Der Marker ist dekorativ, besitzt keinen Tabstop und keinen eigenen
Screenreader-Farbnamen. Fachfarbe erscheint ausschließlich als kleiner Punkt,
kleines Icon oder schmale Akzentfläche; Karten, Berichtstext und PDFs werden
nicht großflächig eingefärbt. Gelb und sehr helle Marker erhalten eine dunkle
Kontur, Schwarz bleibt ein kleiner Akzent.

Fachfarbe, Kursfarbe und Bewertung sind drei getrennte Rollen:

- `courses.color_hex`, `color_key` und `CourseBadge` bleiben ausschließlich
  organisatorischer Kurskontext.
- Die Ratingtokens `--`, `-`, `+`, `++` und ihre vorhandenen Standard-, Sozial-
  und Sportfarben bleiben ausschließlich dokumentierter Entwicklungsstand.
- Status- und Feedbacktones bleiben ausschließlich Bedien- und
  Produktzustände.

Fachmarker werden dort eingesetzt, wo ein sichtbarer Fachname Orientierung
trägt: Dashboard und Stundenplan, Dokumentationsfachauswahl, Beobachtungsdialog
und Beobachtungskarten, Schülerprofil und Fachübersicht, Kompetenz-Cockpit,
Berichtsnavigation/-arbeitsbereich sowie LEG-Auswahl, Kompetenz- und
Evidenzkontext. Untergeordnete Kompetenzzeilen werden nicht mit wiederholten
Markern überladen, wenn der Fachkontext bereits eindeutig ist.

## Informationsdichte und Accessibility - Premium UI Sprint 3

Informationsdichte bedeutet schnellere Erfassbarkeit, nicht mehr sichtbare Information. Produktive Listen und Tabellen priorisieren deshalb je Zeile Identität, fachlichen Kontext, textlich benannten Status und vorhandene Aktion. Sekundäre Metadaten bleiben typografisch ruhig; technische IDs bleiben verborgen oder im Tooltip. Standarddichte sind 44 bis 46 Pixel hohe Tabellenzeilen, kompakte Card-Zeilen und mindestens 28 Pixel hohe Listeneinträge. Lange Texte umbrechen in Inhaltsflächen oder werden in Tabellen mit vollständigem Tooltip angeboten.

`QTableWidget` verwendet als `PremiumTable` keine sichtbaren Gitterlinien, sondern ruhige Zeilentrenner, einen klaren Header sowie zeilenweise Hover-, Auswahl- und Fokuszustände. Inhaltsorientierte Spalten verwenden `ResizeToContents`, dominante Textspalten den verbleibenden Raum. Leere Tabellen werden ausgeblendet und durch `EmptyState` ersetzt. Sortierung wird nur angezeigt, wenn die bestehende Projektion oder Tabelle sie tatsächlich anbietet; Filterzustand bleibt in `FilterBar`, Result Count oder eindeutigem Kontexttext sichtbar. Tabellen sind keine Datenbankansichten und keine fachlichen Datenquellen.

Ganze fachlich aktivierbare Zeilen reagieren konsistent auf Maus und Tastatur: Schülerzeilen öffnen das Profil, Stammdatenzeilen die vorhandene Bearbeitung. Enter und Doppelklick sind gleichwertig; eingebettete Sekundäraktionen bleiben per Tab erreichbar und tragen einen eindeutigen Accessible Name. Nicht interaktive Zeilen erhalten keinen künstlichen Hover oder Hand-Cursor.

Kompetenzdarstellungen behalten verbindlich `Fach → Kompetenzbereich → Thema → Kompetenz`. Einrückung, Surface, Typografie und Abstand unterscheiden die Ebenen auch ohne Farbe. Disclosure und Kontrollkästchen verwenden Standardwidgets, sichtbaren Fokus und Enter beziehungsweise Leertaste. Bericht und LEG leiten keine zweite Hierarchie oder Statuslogik ab.

Statusbadges verwenden ausschließlich die Tones `neutral`, `info`, `success` und `warning`. Der sichtbare Text ist die primäre Bedeutung und wird gleichzeitig als Accessible Name geführt; Farbe darf Bedeutung nur unterstützen. Dasselbe gilt für Dokumentationsabdeckung: Matrixzellen zeigen einen sichtbaren Zahlenwert und nennen im Tooltip beziehungsweise Accessible Name ausdrücklich den Dokumentationsbezug ohne Leistungsbewertung.

Statusbadges reservieren ihre vollständige Textbreite einschließlich zentraler
Innenabstände und dürfen von horizontalen Kartenzeilen nicht unter ihre
lesbare Mindestgröße gedrückt werden. In der Bericht-/LEG-Übersicht gilt das
gleichermaßen für die konkreten Aktionsbeschriftungen unter `Nächste Schritte`;
umbruchfähige Begleittexte nutzen den verbleibenden Raum. Bei 1180 x 760,
1280 x 800 und 1400 x 900 bleiben Chip, Titel und Aktion innerhalb ihrer Karte
sichtbar, ohne einen horizontalen Gesamtscroll zu erzeugen.

`CourseBadge` ist davon bewusst getrennt: Es zeigt ausschließlich organisatorische Kurszugehörigkeit mit immer sichtbarem Kursnamen, kleinem Farbindikator und heller, aus `courses.color_hex` abgeleiteter Kontextfläche. Fehlt eine gültige Kursfarbe, bleibt derselbe Text auf einem neutralen grauen Chip sichtbar. Kursfarben dürfen weder Status, Leistung, Entwicklung noch Dokumentationsgrad ausdrücken und färben keine ganzen Zeilen oder Karten.

Jeder leere Zustand beantwortet in ruhiger Sprache, warum kein Inhalt sichtbar ist und welcher bestehende Schritt weiterführt. Eine leere technische Tabelle, `Keine Daten vorhanden` ohne Kontext oder eine neue fachliche Aktion ausschließlich für den Empty State sind unzulässig. Schreibgeschützte Revisionen erklären statt einer Aktion, dass der eingefrorene Stand unverändert bleibt.

Tastaturgrundlage ist: `Ctrl/Cmd+F` fokussiert die lokale Suche, Escape leert eine befüllte Suche oder schließt gemäß sicherem Dialogvertrag, `Ctrl/Cmd+S` löst die vorhandene Speicheraktion aus, Enter öffnet beziehungsweise aktiviert, Leertaste schaltet Auswahl und Disclosure, Pfeiltasten steuern Segmente, Tabs und LEG-Anker. Fokus folgt der sichtbaren Arbeitsreihenfolge. Alle Eingabefelder, Iconaktionen, Tabellen, komplexen Auswahlen und Primäraktionen besitzen Accessible Names; ergänzende Beschreibungen erklären nur nicht sichtbare Bedienhinweise.

Die produktiven Arbeitsflächen werden bei 1180 x 760, 1280 x 800 und 1400 x 900 sowie mit Device Pixel Ratio 2 geprüft. Primäraktionen und lokale Navigation bleiben sichtbar, horizontale Scrollbereiche entstehen nur bei inhaltlich unvermeidbaren Matrizen, und es gibt keinen horizontalen Gesamtscroll. QPainter wird nicht eingesetzt; Standardwidgets und zentrale QSS-Zustände liefern den erforderlichen High-DPI-, Fokus- und Screenreader-Nutzen.

## Dialog Experience und Workspace Polish - Premium UI Sprint 2

Produktive PySide-Dialoge verwenden drei Groessenrollen: kleine Dialoge fuer eine kompakte Eingabe, mittlere Dialoge fuer mehrere klar getrennte Feldgruppen und grosse Dialoge als temporaere Arbeitsraeume. Grosse Arbeitsdialoge behalten ihren fachlich freigegebenen Aufbau; die Groessenrolle veraendert weder Navigation noch Workflow. Bei 1180 x 760 bleiben Kopf, zentrale Orientierung und Pflichtaktionen sichtbar, bei 1400 x 900 wird zusaetzlicher Raum den Arbeitsflaechen gegeben.

Komplexe Dialoge verwenden `DialogHeader` mit Kontexticon, fachlich eindeutigem Titel, sichtbarem Kind-, Entwurfs- oder Verwaltungskontext, optionaler Kurzbeschreibung und ruhiger Trennlinie. Der Fenstertitel allein traegt die Orientierung nicht. Kleine Eingabedialoge gruppieren Felder in `AppCard`-Flaechen mit `SectionHeader`; Labels stehen direkt oberhalb der Felder. `QFormLayout` bleibt ausschliesslich Layouttechnik und bestimmt nicht mehr die sichtbare Form-Anmutung.

Die Aktionszone bleibt am unteren Rand beziehungsweise bei grossen Workspaces ausserhalb des dominanten Scrollbereichs sichtbar. Sekundaere oder ruhige Aktionen stehen links von genau einer primaeren Speicher- oder Bestaetigungsaktion. Speichern ist bei einfachen Eingabedialogen die Enter-Standardaktion, Escape bricht ab. Bei verlustkritischen Arbeitsdialogen ist `Weiter bearbeiten` die sichere Standardwahl; destruktives Verwerfen wird textlich benannt und nie nur durch Farbe vermittelt.

Validierungs- und Speicherfehler erscheinen als `InlineMessage` am betroffenen Kontext. Erfolgreiches Speichern darf weiterhin ueber den vorhandenen `Toast` bestaetigt werden. Native `QMessageBox`-Fehler und -Bestaetigungen erhalten die zentrale Typografie, Mindestbreite und Buttonflaeche; irreversible Spezialbestaetigungen behalten ihre bereits freigegebenen Texte und Schutzmechanismen.

Der Beobachtungsdialog unterscheidet die vorhandenen drei Zonen sichtbar als ruhigen Kontext, dominante Kompetenzarbeit und Eingabe-/Aktionsbereich, ohne Auswahl oder Speicherpfad zu veraendern. Berichtswerkstatt und finale Revision verwenden denselben Dialogkopf, unterscheiden bearbeitbaren Draft, Vorschau und schreibgeschuetzte Revision aber weiterhin ueber vorhandene Status- und Dokumentflaechen. Der LEG-Workspace verbindet Kindkontext, sechs gruppierte Inhaltsanker, Dirty-State und feste Aktionsleiste in derselben Kopfsprache.

Premium UI Sprint 2 fuehrt keine neue Motion ein. Vorhandene `InlineMessage`-, `Toast`-, Segment- und Disclosure-Motion bleibt zentral, kurz und Reduced-Motion-sicher. Dialog-Fades, Hoehenanimationen, verschachtelte Animationen und QPainter-Spezialelemente sind fuer diesen Sprint nicht gerechtfertigt.

## LEG-Workspace-Sprache - UI Sprint 6B

Der Lernentwicklungsgespraech-Draft verwendet `PageHeader`, `StatusBadge`, `SectionHeader`, `AppCard`, `SearchField`, `FilterBar`, `InlineMessage`, `Toast` und zentrale Buttonrollen als einen zusammenhaengenden kindbezogenen Workspace. Kopf, lokale Ankerleiste und Aktionsleiste bleiben ausserhalb des dominanten Anker-Scrollbereichs. Die linke Leiste zeigt alle sechs vollstaendigen Inhaltstitel in den drei sichtbaren Arbeitskontexten `Vorbereitung`, `Im Gespräch` und `Vereinbarungen & Abschluss` sowie genau einen textlich markierten aktuellen Anker. Die Gruppen besitzen keine eigene Seite und keine zusaetzliche Klickebene.

Ankerstatus ist neutraler lokaler UI-State: `Aktuell`, `Inhalt vorhanden` und `Noch leer`. Nummern, Haken, Prozentwerte, Ampelfarben, Leistungsdarstellung und Fortschrittsbegriffe sind unzulaessig. Der aktive Eintrag wird durch Flaeche, Schriftgewicht, linken Marker und Statustext vermittelt, nie allein durch Farbe. Klick, Enter und Space waehlen jeden Anker direkt; Pfeil hoch/runter sowie Home/End navigieren die sichtbare Gruppenreihenfolge nach Qt-Konvention.

Die aktive Phase verwendet dieselbe zentrale helle Blue-Auswahlflaeche und
Brand-Blue-Markierung wie die Berichtswerkstatt sowie dasselbe strukturelle
Aktivmuster wie die Beobachtungsnavigation. `Inhalt vorhanden` bleibt
bei inaktiven Phasen eine ruhige textliche Unterzeile; `Noch leer` bleibt ohne
Akzent. Die gruene LEG-Kontextfarbe bleibt auf Kopf und kleine Kontextdetails
begrenzt und erhaelt keine Abschluss- oder Erfolgsbedeutung.

Die drei Inhaltsrollen bleiben auch ohne Farbe eindeutig. `Nur für die Vorbereitung` nutzt eine ruhige `AppCard[soft]`, `Im Gespräch bearbeiten` eine normale Schreibflaeche und `Im Entwurf als Vereinbarung festgehalten` sparsam `AppCard[accent]`. Rollenlabel, SectionHeader, Hilfetext, Einrueckung und Typografie verhindern, dass interne Vorbereitung wie eine gemeinsame Vereinbarung wirkt. Alle mehrzeiligen LEG-Editoren besitzen rollen- und phasenbezogene Accessible Names.

Kompetenz-, Beobachtungs- und Diagrammauswahl liegt ausschliesslich im Anker `evidence` unter `Vorbereitung` und traegt sichtbar den Hinweis `Vorbereiten · im Gespräch bei Bedarf`. Andere Anker verwenden eine read-only `AppCard[soft]`-Zusammenfassung mit der sekundaeren Aktion `Belege ansehen`. Historisch und nicht verfuegbar werden textlich benannt. Optionale Gespraechsbilder bleiben standardmaessig geschlossen. Auswahl, Suche und Disclosure verwenden die bestehenden sofortigen Zustandswechsel und hoechstens eine zentrale Opacity-Bestaetigung; Reduced Motion zeigt Endzustaende unmittelbar.

Die untere LEG-Aktionsleiste besitzt mit `Entwurf speichern` genau eine primaere Aktion. `Belege ansehen` und `Schließen` bleiben sekundaer oder quiet; lineare Aktionen `Zurück` und `Weiter` erscheinen nicht. Eine `InlineMessage` steht unmittelbar oberhalb der Leiste; erfolgreicher Speicherstatus darf zusaetzlich als Toast erscheinen. Bei Dirty-Close ist der ruhige Drei-Wege-Dialog mit `Entwurf speichern`, `Änderungen verwerfen` und `Weiter bearbeiten` verbindlich.

Responsive Regel: bei 1400 x 900 ist die Phasenleiste 232 px, bei 1280 x 800 etwa 220 px und bei 1180 x 760 214 px breit. Es gibt keine Mindestbreite von 1200 px, keinen horizontalen Gesamtscroll und pro aktiver Phase hoechstens einen dominanten vertikalen Scrollbereich. Kopfmetadaten duerfen ruhig umbrechen; Pflichtaktionen bleiben sichtbar.

## Kindbezogene Workspace-Sprache - UI Sprint 4

UX-Ergänzung 07.09.2026: `Speichern & weitere` liegt als sekundärer Button
unter der bestehenden Beobachtungs-Aktionsleiste. `Speichern` bleibt die
einzige primäre Aktion. Der Button ist per Tab/Space erreichbar, kein
Defaultbutton und bei Bearbeitung verborgen. Nach Erfolg erhalten neue
Normalbeobachtungen die Katalogsuche, Schnellbeobachtungen die leere Notiz als
Fokusziel. Die bestehende Drei-Zonen-Struktur und getrennte Scrollbereiche
bleiben erhalten.

UX-Ergänzung 07.09.2026: `⌘N` ergänzt die vorhandenen Beobachtungsbuttons.
Ohne sichtbaren eindeutigen Kindkontext öffnet die Aktion die Schülerliste
mit fokussierter Suche und dem Hinweis, ein Kind auszuwählen. Autorepeat ist
deaktiviert; offene Dialoge, Popups und andere aktive Fenster bleiben alleinige
Tastatureigentümer. Eingabetexte werden durch das Kürzel nicht verändert.

UX-Ergänzung 07.09.2026: Der einmalige Startfokus im Beobachtungsdialog
liegt für Neu in der Katalogsuche, für Bearbeiten und Schnellbeobachtung in
der Notiz. Er verwendet den vorhandenen Fokusrahmen, selektiert oder ändert
keinen vorhandenen Text und wird beim erneuten Anzeigen nicht erzwungen.

Schuelerprofil, Kompetenz-Cockpit und Beobachtungsdialog bilden einen zusammenhaengenden paedagogischen Workspace. Die Hierarchie ist verbindlich: zuerst Kind und aktueller Kontext, danach primaere paedagogische Information, relevante Aktion, sekundaere Details und zuletzt historische beziehungsweise ergaenzende Inhalte. Der Kindername bleibt im Profilkopf und im Dialog-`PageHeader` dauerhaft sichtbar. Im Profil markiert genau eine blaue Primaeraktion `Neue Beobachtung`; Datei und seltenere bestehende Aktionen bleiben sekundaer.

Das Profil nutzt `AppCard[accent]` fuer den kompakten Kindkontext, `SegmentedControl` fuer die lokale Navigation sowie `SectionHeader`, `FilterBar`, `SearchField`, `FilterChip`, `StatusBadge` und `EmptyState` fuer bestehende Inhalte. Beobachtungen erscheinen als scanbare Kartenzeilen: Datum und Fach bilden den Kopf, Kontext und Notiz bleiben darunter ruhig, Details und Bearbeiten sind bewusst erreichbar. Leere Beobachtungslisten bieten genau die naechste sinnvolle Aktion an.

Lernentwicklungskarten sind keine Beobachtungslisten und keine Leistungsvisualisierung. Jede Karte nennt Kompetenz und Fach/Thema, stellt genau eine textlich benannte Ausgangslage einem aktuellen dokumentierten Stand gegenueber und zeigt darunter den datierten realen Ausloeser als Beobachtung oder Bestaetigung. `--`, `-`, `+` und `++` erhalten zur Orientierung dezente Rosa-, Gelb- und Gruenabstufungen; Text bleibt die primaere Bedeutung, der Pfeil bezeichnet nur die Veraenderung zwischen zwei realen Zustaenden. Die ganze Karte ist per Maus, Fokus sowie Enter/Leertaste bedienbar. Historische Referenzen bleiben ein sekundaeres Badge. Es entstehen keine Scores, Trends, Empfehlungen, Interpolationen oder neuen Bewertungsregeln.

Im Kompetenz-Cockpit wird Hierarchie auch ohne Farbe ueber Einrueckung, Typografie, Abstand und Surface unterschieden. Fach nutzt eine ruhige Akzentflaeche, Kompetenzbereich eine weiche Flaeche, Thema eine normale Flaeche und die Kompetenz eine linksbuendige Disclosure-Zeile. Lange Kompetenztexte umbrechen in Details und Auswahllisten. Neutrale Fortschrittsbalken und Zaehler beschreiben ausschliesslich Dokumentationsabdeckung; historische Zeilen tragen eine eindeutige ruhige Kennzeichnung.

Der Beobachtungsdialog behaelt drei Zonen: `Kind und Kontext`, `Ausgewaehlte Kompetenzen / Kompetenzkatalog` sowie `Beobachtung / Dokumente / Aktionen`. Der Katalog nutzt dieselbe Segment-, Such-, Card- und Badge-Sprache. Ausgewaehlte Kompetenzen zeigen Bewertung immer sichtbar als vier beschriftete Chips. Dateizeilen zeigen Dateiname, Typ und eine klar benannte Entfernen-Aktion. `InlineMessage` steht unmittelbar vor der persistenten Speicherleiste.

Die vier Chips behalten Palette, Auswahlhaken und gespeicherte Tokens. Das
Standardprofil verwendet unverändert `++ sicher erreicht`, `+ erreicht`,
`- in Entwicklung`, `-- Unterstützungsbedarf`. Ausschließlich Selbst- und
Sozialkompetenz zeigt `Kaum vorhanden`, `Teilweise`, `Gut`, `Ausgeprägt`;
ausschließlich Sport zeigt `Erste Übungen`, `Übt noch`, `Meist`, `Sicher`.
Pflanzenbilder und Pflanzenstufen sind ausschließlich für den unten
freigegebenen Kompetenz-PDF-Export vorgesehen. Schulbesuchsjahr-Farben
und Pflanzen in der allgemeinen App-Oberfläche bleiben ausgeschlossen.

Disclosure setzt Sichtbarkeit und Datenzustand sofort und verwendet nur eine zentrale Opacity-Bestaetigung von maximal `MOTION_FAST_MS`. Keine Hoehenanimation langer Listen, keine verschachtelten Animationen und kein Layoutflackern. Reduced Motion zeigt den Endzustand unmittelbar. Die Arbeitsbereiche werden fuer 1400 x 900, 1280 x 800 und 1180 x 760 geprueft; Pflichtaktionen bleiben sichtbar, der Dialog besitzt getrennte vertikale Scrollbereiche und keinen horizontalen Katalog- oder Gesamtscroll.

Accessibility-Regel: Die verbleibende lokale Fachnavigation ist per
Pfeiltasten bedienbar; Disclosure, Kompetenzwahl und Bewertung reagieren auf
Fokus sowie Enter/Space. Datum, Fach, Kontext, Notiz, Suche, Bewertung,
Entfernen und Speichern besitzen Accessible Names. Der Beobachtungsdialog
und das Kompetenz-Cockpit erzeugen für den einheitlichen
Entwicklungsbuch-Katalog keine bedeutungslose Stage-Steuerung. Keine
Information wird ausschliesslich durch Farbe vermittelt.

QPainter-Regel: UI Sprint 4 verwendet keinen QPainter. Timeline-Marker, Spezial-Focus-Ringe oder Evidenzgrafiken erzeugen gegenueber den vorhandenen Standardwidgets keinen ausreichenden Mehrwert; zentrale Qt-Widgets und QSS bleiben High-DPI-, Fokus- und Reduced-Motion-sicherer.

## Motion System - UI Sprint 3

Motion unterstuetzt Orientierung und Rueckmeldung, ohne Arbeitsablaeufe zu verlangsamen. Die zentrale Implementierung liegt in `src/desktop_app/motion.py`; Screens besitzen keine eigene Animationslogik. Verbindliche Dauern sind `80 ms` fuer Pressed, `100 ms` fuer Hover, `120 ms` fuer direkte Rueckmeldung, `160 ms` fuer Auswahl und lokalen Inhaltswechsel, `180 ms` fuer normale Uebergaenge, `200 ms` fuer Dialoge sowie `220 ms` fuer Toasts. `240 ms` bleibt die Obergrenze fuer groessere seltene Rueckmeldungen. Standard-Easing ist `OutCubic`, Ausblendungen verwenden `InCubic`. Feder-, Bounce-, elastische und pulsierende Verlaeufe bleiben ausgeschlossen.

Die globale `MotionPolicy` besitzt genau einen Reduced-Motion-Schalter. Im reduzierten Modus werden fachlicher Zustand, Sichtbarkeit, Fokus und Endwerte sofort gesetzt. Timer duerfen weiterhin die Lesedauer einer Meldung steuern, erzeugen aber keine Bewegung. Animationen werden pro Widget und semantischem Schluessel ersetzt statt gestapelt; Qt-Ownership und Aufraeumen bei Abschluss beziehungsweise Widget-Zerstoerung sind Bestandteil des zentralen Vertrags. Eine spaetere verlaessliche Qt-/Plattformanbindung setzt ausschliesslich diese Policy und erfordert keine Aenderung an Komponenten; UI Sprint 3 erzwingt dafuer keine neue sichtbare Einstellung.

Komponenten mit Motion:

- semantisch konfigurierte Buttons: kurze Hover-, Pressed- und Fokusantwort; Disabled bleibt statisch und eindeutig
- `AppCard` nur bei `interactive`: dezenter, layout-neutraler Hover-Schatten; Pressed, Fokus und Auswahl bleiben sofort sichtbar
- `SegmentedControl`: gleitender lokaler Auswahlindikator plus kurze Opacity-Bestaetigung des bereits gesetzten Zielsegments; Signal und Navigation werden nicht verzoegert
- Sidebar-Navigation: ausschliesslich der drei Pixel breite Auswahlindikator bewegt sich; Eintrag, Screen und Inhalt wechseln sofort
- Bewertungsbadges: Auswahl und sichtbarer Haken werden mit einer kurzen Fade-Bestaetigung quittiert
- `FilterChip`: Einblenden eines neu sichtbaren Filterzustands; Reset und Filterausfuehrung bleiben unmittelbar
- `InlineMessage`: ruhiges Einblenden neuer Information oder Erfolgsmeldung; Warnungen und Fehler erscheinen sofort
- `MotionDialog`: steht für kleine, nicht arbeitskritische Dialoge zur Verfügung; die drei Pilot-Arbeitsdialoge Bericht, LEG und Beobachtung verwenden den statischen `QDialog`-Pfad
- persistente Primaer-Speicheraktionen: kurzer bestaetigender Zustand nach fachlich bestaetigtem Erfolg
- `Toast`: statische, compositingfreie Anzeige, Hover-Pause und sichere Ersetzung einer laufenden Meldung; Text, FontMetrics, Umbruch, Padding und vorhandene Icons bestimmen zentral Breite und Höhe innerhalb sicherer Parent-Abstände

Bewusst statisch bleiben `EmptyState`, Tabellen und Tabellenzeilen, grosse Listen, Scrollen, Baumstrukturen, Suchergebnisse, nicht interaktive Karten, Dokument- und PDF-Vorschauen, die komplette Product Shell sowie Dashboard-Flaechen ohne bewussten Kontextwechsel. Für den Pilot bleiben Bericht-Workspace, LEG-Anker und Beobachtungs-Kompetenzbereich einschließlich ihrer Arbeitsdialoge frei von Opacity-/GraphicsEffect-Animationen; Disclosure setzt dort ausschließlich den Sichtbarkeitszustand. Es gibt keine vollflaechigen Screen-Uebergaenge, Hoehenanimationen, verschachtelten Listenanimationen oder blockierenden Animationen. Geometrie wird ausschliesslich fuer die kleinen Segment- und Sidebar-Indikatoren animiert; Layout und Inhaltsflaechen bleiben unberuehrt.

## Component Library V2 - UI Sprint 2

Bestandskomponenten, die erweitert werden:

- `PageHeader`: klare Titel-/Untertitelhierarchie und stabile Aktionszone
- `SearchField`: Suchicon, native Clear-Aktion, Escape-Reset und sichtbarer Fokus
- `StatusBadge`: semantische, aber fachlich neutrale Tones
- `EmptyState`: optionale Ueberschrift, Erklaerung und genau eine passende Aktion
- `SegmentedControl`: kompakte lokale Navigation mit Maus, Fokus und Pfeiltasten
- `InlineMessage` und `Toast`: kontextgebundene beziehungsweise fluechtige Rueckmeldung

Neue notwendige Basiskomponenten:

- `AppCard`: Surface-Vertrag mit `default`, `soft`, `accent` und `interactive`; nur interaktive Karten erhalten Hover und Auswahlzustand
- `SectionHeader`: Abschnittstitel, optionale Kurzbeschreibung, Hilfe und Aktionen
- `FilterBar`: komponiert vorhandene Suche, aktive Filter und Reset, besitzt aber keine Filterlogik
- `FilterChip`: zeigt lokalen Filterstate; `selected`, Fokus und Disabled sind rein semantische UI-Zustaende
- `IconButton`: kompakte Aktion mit SVG-Icon, Tooltip und verpflichtendem Accessible Name

Bewusst nicht als eigene Komponenten eingefuehrt werden `DashboardCard`, `InfoCard`, `MetricCard`, `StudentRow` und `GroupCard`: Sie werden durch `AppCard`-Varianten, bestehende Qt-Tabellenzeilen und komponierte Screen-Inhalte belastbar abgedeckt. Eine Spezialklasse ohne zweiten Nutzungskontext waere nicht gerechtfertigt.

Surface-Hierarchie:

1. App-Hintergrund trennt globale Arbeitsflaechen.
2. `AppCard[cardVariant="default"]` bildet normale Inhaltsflaechen.
3. `soft` gruppiert sekundaere Informationen ohne zusaetzliche Elevation.
4. `accent` markiert genau eine primaere Situation, zum Beispiel die aktuelle beziehungsweise naechste Stunde.
5. `interactive` kennzeichnet klickbare Karten durch Cursor, Hover, Fokus und optional `selected`; nicht klickbare Karten reagieren nicht auf Hover.

Filterregel: Suche bleibt je Schuelerliste lokal. Der sichtbare Kontextfilter stammt aus dem bestehenden Shell-/Workspace-State. Reset erscheint nur fuer einen aktiven Kontextfilter und kehrt zur ausloesenden Auswahl zurueck. Ein Segmentwechsel laedt dessen bestehenden Kontext neu; es entsteht keine persistente oder parallele Filterhaltung.

QPainter-Regel: UI Sprint 2 verwendet keinen QPainter. Karten, Fokus, Chips, Tabellen, Timeline und Matrix lassen sich mit Standardwidgets und zentralem QSS hochwertig und High-DPI-sicher umsetzen. QPainter bleibt kuenftigen visuellen Elementen vorbehalten, fuer die Standardwidgets nachweislich nicht ausreichen.

Das freigegebene App-Icon ist ab der PySide-Hauptanwendung die zentrale gestalterische Referenz fuer den Jenaplan-Kompetenzmanager.

Das aktuelle Design der Stammgruppenübersicht wurde durch Laura freigegeben.

Dieses Design ist die verbindliche Referenz für alle zukünftigen Ansichten.

Neue Screens sollen visuell an das App-Icon anschliessen.

Leitregel:

> Der Jenaplan Kompetenzmanager wirkt wie eine moderne paedagogische Entwicklungs-App: ruhig, klar, wachstumsorientiert, datenbewusst und freundlich.

## Verbindliche Eigenschaften

Zum freigegebenen Design gehören:

- Bezug zum freigegebenen App-Icon
- Farbwelt
- Typografie
- Kartenlayout
- Kartenabstände
- Desktop-App-Anmutung
- 140-%-Zoom der Stammgruppenübersicht
- Suchfeld
- Weißraum
- visuelle Hierarchie

## Geltungsbereich

Alle zukünftigen Ansichten müssen sich an diesem Design orientieren.

Das gilt insbesondere für:

- PySide-Hauptnavigation
- Dashboard / Startseite
- Schuelerliste
- Stammgruppenübersicht
- Kursübersicht
- Schülerprofil
- Beobachtungsdialoge
- Stammdaten
- Kompetenzansichten
- Auswertungen und Berichte
- App-Info und Statusbereiche
- zukünftige Verwaltungsansichten
- zukünftige Dialoge, Dialogseiten und experimentelle UserForms

## App-Icon als visuelle Leitlinie

Das App-Icon verbindet Baum, Personen, Diagramm und schützenden Bogen zu einem ruhigen, hochwertigen Zeichen fuer paedagogische Entwicklungsarbeit.

Die Anwendung soll daraus folgende Grundidee ableiten:

- modern, ruhig, freundlich und professionell
- klar strukturiert, aber nicht administrativ schwer
- wachstumsorientiert und schuelerbezogen
- datenbewusst, ohne technisch-kuehle Verwaltungsoptik
- hochwertig wie eine moderne Desktop-App, nicht wie eine klassische Excel- oder Tabellenanwendung

Die Gestaltung soll Wachstum, Schuelerbezug, Kompetenzentwicklung und Auswertung gleichzeitig sichtbar machen.

### Bedeutungsanker

- Baum: Wachstum, Lernentwicklung und langfristige Kompetenzentwicklung
- Personen: Schuelerbezug, paedagogische Beziehung und konkrete Arbeit mit Kindern
- Diagramm: Auswertungen, Kompetenzverlaeufe und Berichte
- Kreis/Bogen: Ganzheitlichkeit, Ueberblick, Schutzraum und strukturierter Rahmen
- farbige Blaetter: individuelle Lernwege und unterschiedliche Entwicklungsfelder

Diese Bedeutungsanker sollen bei spaeteren UI-Entscheidungen beruecksichtigt werden.

### Farbwelt aus dem Icon

Die Icon-Palette ist die Grundlage fuer die kuenftige PySide-Oberflaeche.

- Dunkelblau: Struktur, Professionalitaet, Navigation, Auswertung
- Blau: Klarheit, Primaeraktion und zentrale Auswahl
- Tuerkis: Entwicklung, Fokus, Dokumentation und Beobachtungsarbeitsraum
- Gruen: Wachstum, Lernen und LEG-Arbeitsraum
- Limettengruen: sparsamer organischer Markenakzent
- Orange: Schreiben, Berichtskontext und offene Dokumentationspunkte
- helle neutrale Hintergruende: Ruhe, Lesbarkeit, Konzentration

Die Farben werden nicht grell oder verspielt eingesetzt. Sie sollen modern, ausgewogen und hochwertig wirken.

Kursfarben, Diagrammfarben, Statusmarker und Aktionsfarben sollen sich aus dieser Icon-Farbwelt ableiten.

### Formensprache

Die App verwendet eine weiche, leichte Formensprache:

- abgerundete Formen
- Kartenoptik statt Tabellenoptik, wo sinnvoll
- grosszuegige Abstaende und Weissraum
- klare visuelle Hierarchie
- freundliche Icons und Marker
- ruhige, moderne Oberflaechen
- keine ueberladene Verwaltungsoptik
- keine harte Tabellen- oder Excel-Anmutung als Hauptstil

Schuelerprofile sollen als ruhige Karten mit klaren Bereichen erscheinen.

Das freigegebene Variante-A-Arbeitsprofil verwendet einen kompakten Profilkopf mit Initialenavatar, Stammgruppen-/Kurskontext, neutralem Dokumentationsring und genau einer blauen Primaeraktion `Beobachtung erfassen`. Die erste Uebersichtsreihe besteht aus einer breiten Orientierungskarte sowie den schmaleren Karten `Kompetenzen` und `Noch nicht dokumentiert`. Bei geringerer Inhaltsbreite steht die Orientierungskarte oberhalb der beiden Informationskarten. Der Ring und alle Counts beschreiben ausschließlich Dokumentationsumfang; fehlende Dokumentation bleibt neutral. Die Orientierungskarte zeigt hoechstens drei textlich vollstaendige, belegverknuepfte Statuswechsel und verwendet keine Diagramm-, Score-, Ampel- oder Trendsemantik.

Das Kompetenz-Cockpit im Schuelerprofil nutzt verschachtelte, abgerundete Karten und neutrale Fortschrittsbalken. Fortschritt visualisiert ausschließlich Dokumentationsabdeckung und verwendet keine Bewertungs- oder Ampelfarben. Die Darstellung erweitert das bestehende Kartensystem, ohne eine neue Farbsemantik oder ein spaeteres Designsystem vorwegzunehmen.

Beobachtungen sollen bevorzugt als leichte Cards oder geordnete Listen mit klarer Hierarchie gestaltet werden, nicht als reine Tabellenlisten.

Auswertungen und Berichte sollen Diagrammfarben aus der Icon-Palette verwenden.

Wichtige Aktionen duerfen farblich klar hervorgehoben werden, bleiben aber zurueckhaltend und serioes.

### Moderne leichte Glasoptik

Wenn technisch und gestalterisch sinnvoll umsetzbar, darf die PySide-App eine leichte moderne Glasoptik aufgreifen.

Gemeint ist:

- helle, leicht transparente oder weich abgesetzte Flaechen
- dezente Schatten
- sanfte Rahmen
- leicht schwebende Karten und Panels
- ruhige, helle Hintergruende
- moderne Tiefe ohne starke Effekte

Glasoptik ist ein Stilmittel, kein Selbstzweck.

Verbindliche Grenzen:

- Lesbarkeit hat Vorrang.
- Kontraste muessen barrierearm bleiben.
- Transparenzen duerfen Texte nicht schwer lesbar machen.
- Keine uebertriebene Glassmorphism-Optik.
- Die App bleibt serioes und paedagogisch professionell.

### Zu vermeiden

- keine Excel- oder Tabellenoptik als Hauptanmutung
- keine ueberladene Admin-Oberflaeche
- keine grellen Primaerfarben
- keine unruhigen Verlaeufe
- keine uebertriebene Glasoptik
- keine verspielte Kinder-App-Optik
- keine schlechte Lesbarkeit durch Transparenzen
- keine Designaenderungen ohne Bezug zur Icon-Farbwelt

## PySide-Hauptanwendung

PySide ist die Hauptanwendung des Jenaplan-Kompetenzmanagers.

Neue UI-Entwicklung konzentriert sich auf die PySide-App.

Excel/VBA ist nicht mehr die Zielrichtung fuer die Haupt-App. Der alte Excel-/VBA-Stand liegt nur noch im Legacy-Archiv `legacy/excel/`; neue UI-Entwicklung konzentriert sich auf PySide.

### PySide Theme Umsetzung

Die freigegebene Icon-Leitlinie wird in der PySide-App ueber ein zentrales Theme-Modul umgesetzt.

Das Theme buendelt:

- die Icon-Farbwelt fuer Navigation, Primäraktionen, Statusmarker und ruhige Flaechen
- helle neutrale App-Hintergruende
- weiche Karten- und Panel-Flaechen mit sanften Rahmen
- einheitliche Tabellen-, Eingabe- und Button-Stile
- semantische Textrollen fuer App-Titel, Screen-Titel, Dialogtitel, Kartenueberschriften, Hinweise und Fehlermeldungen

Neue PySide-Screens und Dialoge sollen dieses Theme verwenden, statt eigene Farb- oder Kartenstile lokal zu definieren.

Das App-Icon wird als sichtbares Branding in der PySide-Hauptanwendung verwendet:

- klein und ruhig oberhalb der Hauptnavigation in der Seitenleiste
- groesser und zentriert oben im App-Info-Dialog

Das Icon ist Branding und Bedeutungsanker, keine dekorative Ueberladung. Es darf die Navigation, Dialogtexte oder fachliche Inhalte nicht verdecken.

Die leichte Glasoptik wird technisch ueber helle, weich abgesetzte Flaechen, sanfte Rahmen und dezente Kontraste simuliert. Echte macOS-Transparenz oder schwer wartbare Spezialwidgets sind nicht Bestandteil des Design-Systems.

### UI Sprint 1: Design Tokens und Grundkomponenten

Die PySide-Hauptanwendung verwendet die native Systemschrift. Eine feste Schriftfamilie wie Arial wird nicht gesetzt. Semantische Typografierollen definieren Hierarchie, Gewicht und Groesse, ohne die Plattformtypografie zu ersetzen.

Verbindliche Token-Stufen:

- Abstaende: `4`, `8`, `12`, `16`, `24`, `32`, `48`
- Radien: klein, mittel, gross und extra gross
- Elevation: flach, Karte und Overlay; Tiefe bleibt dezent und dient nur der Hierarchie
- Motion: schnell `120 ms`, Standard `180 ms`, langsam `240 ms`; Animationen sind optional und duerfen Bedienung oder Tests nicht blockieren
- Farben: Hintergrund, Oberflaeche, Rahmen, Text, Fokus, Information, Erfolg, Warnung und Fehler werden semantisch benannt

Verbindliche Buttonrollen:

- `primary`: genau die wichtigste Seiten- oder Speicheraktion
- `secondary`: normale explizite Aktion
- `quiet`: untergeordnete Aktion ohne visuelles Gewicht
- `destructive`: bestaetigungspflichtige destruktive Aktion
- `icon`: kompakte Aktion mit zugaenglichem Namen und Tooltip
- `link`: Navigation innerhalb eines fachlichen Kontexts

Alle Rollen besitzen Normal-, Hover-, Fokus-, Pressed- und Disabled-Zustaende. Speichern bleibt primaer; Abbrechen bleibt sekundaer. Lokale Stylesheets duerfen fuer diese Interaktionsrollen nicht verwendet werden.

Registrierte Grundkomponenten sind `PageHeader`, `SegmentedControl`, `SearchField`, `StatusBadge`, `InlineMessage`, `EmptyState` und `Toast`. `NavigationItem` ist die semantische Definition eines Shell-Eintrags. Nicht blockierender Erfolg erscheint als Toast; dauerhaft handlungsrelevante Information, Warnung oder Validierung steht inline am betroffenen Kontext. Modale Dialoge bleiben fuer irreversible Bestaetigungen und Fehler, die ein Fortsetzen verhindern.

Die Shell verwendet ein konsistentes Outline-SVG-Set mit den Groessenrollen `16`, `20` und `24`. Zufaellige Unicode-Zeichen sind keine Shell- oder Aktionsicons. Fachlich variable Kursfarben werden als kleine neutrale Flaechenmarker dargestellt.

Fokus folgt der sichtbaren Arbeitsreihenfolge. Alle interaktiven Elemente sind per Tab erreichbar; segmentierte Navigation reagiert zusaetzlich auf Links/Rechts, Suche auf Escape und Tabellenaktivierung auf Enter beziehungsweise Doppelklick. Iconaktionen und nicht selbsterklaerende Controls erhalten zugaengliche Namen und Tooltips.

Dokumentationsabdeckung verwendet ausschliesslich neutrale Blau-Grau-Abstufungen. Sie ist keine Bewertung, keine Leistung und keine Ampel. Gruen, Orange und Rot duerfen in dieser Matrix keinen vermeintlich guten, mittleren oder schlechten Kompetenzstand codieren.

## Änderungsregel

Normale Entwicklungssprints verändern das Design nicht.

Designänderungen dürfen ausschließlich über einen eigenen UX-Sprint erfolgen.

Ein UX-Sprint benötigt:

- UX-Review
- Product-Owner-Freigabe
- anschließende dokumentierte Umsetzung

## UX-Prototypen fuer Eingabedialoge

Neue Eingabedialoge werden nicht frei im VBA-Designer oder direkt im Workbook gestaltet.

Vor der technischen Umsetzung muss ein UX-Prototyp als verbindliche visuelle Referenz entstehen.

Der Ablauf lautet:

1. UX-Prototyp erstellen
2. UX-Review mit Laura bzw. Product Owner durchfuehren
3. UX-Freigabe dokumentieren
4. worksheet-basierte Dialogseite moeglichst 1:1 nach dem freigegebenen UX-Prototyp umsetzen
5. Validierung, Adapter-Anbindung und fachliche Logik erst danach ergaenzen

Der UX-Prototyp ist keine technische Implementierung. Er enthaelt keine VBA-Events, keine Validierung, keine Adapter-Anbindung, keine SQLite-Kommunikation und keine fachliche Logik.

Feature 1 `Neuer Schueler`:

- Die Datei `output/Jenaplan_UX_Prototype_v0.1.xlsx` enthaelt das Blatt `Feature 1 – Neuer Schüler`.
- Dieses Blatt ist die visuelle Vorlage fuer die worksheet-basierte Dialogseite `dlg_neuer_schueler`.
- Enthalten sind Fenstertitel, Pflichtfelder Vorname, Nachname, Stammgruppe und Kurs, Notizbereich, Dokumentbereich mit Empty State, Button `+ Dokument hinzufügen` sowie die Buttons Abbrechen und Speichern.

## Architekturregel

Das Design-System ist Source of Truth für sämtliche Benutzeroberflächen.

Python erzeugt Benutzeroberflächen aus dem freigegebenen Design-System.

VBA implementiert ausschließlich Interaktion und verändert keine fachliche Logik.

## Worksheet-basierte Dialogseiten

Worksheet-basierte Dialogseiten sind ab Feature 1 das primaere Eingabe-Pattern fuer Excel auf macOS.

Sie folgen dem ruhigen, einfachen Desktop-App-Charakter des freigegebenen Designs.

Sie sind eigene geschuetzte Arbeitsblaetter, die wie Dialoge gestaltet sind.

Sie sammeln Eingaben, enthalten keine Businesslogik, schreiben nicht direkt in fachliche Tabellen und rufen spaeter ausschliesslich freigegebene Adapter auf.

Standard fuer `dlg_neuer_schueler`:

- sichtbarer Fenstertitel `Neuer Schüler`
- eigene Dialogseite `dlg_neuer_schueler`
- geschuetztes Arbeitsblatt mit freigegebenen Eingabebereichen
- einspaltiger Aufbau von oben nach unten
- Pflichtfelder sichtbar mit `*`
- Dokumentbereich als einfache Liste mit Empty State
- Buttons unten rechts: Abbrechen links, Speichern rechts
- Abbrechen navigiert spaeter zur aufrufenden Ansicht zurueck
- Speichern wird erst mit Validierung und Adapter-Anbindung produktiv

## Deprecated: Modale VBA-UserForms

Modale UserForms folgen dem ruhigen, einfachen Desktop-App-Charakter des freigegebenen Designs.

Sie sind Eingabedialoge der Anwendung und keine Tabellenansichten.

VBA-UserForms sind auf Excel fuer macOS nicht mehr das primaere Eingabe-Pattern.

`frm_student_new` bleibt als experimenteller Artefaktstand erhalten, ist aber nicht produktiv freigegeben.

Keine weiteren AppleScript-Tests mit `do Visual Basic` werden fuer UserForms verwendet.

Historischer Dialogstandard:

Standard-Fenster:

- Standardgroesse fuer einfache Eingabedialoge: ca. 5760 x 6720 Twips
- modales Oeffnen
- Titel ueber die Fenster-Caption, kurz und fachlich eindeutig
- einspaltiger Aufbau von oben nach unten
- linker und rechter Rand ca. 480 Twips
- vertikale Abstaende zwischen Label und Feld ca. 300 Twips
- groessere Abschnittsabstaende zwischen Feldgruppen

Standard-Labels:

- klare Ueberschrift
- einspaltige, gut lesbare Pflichtfelder
- Pflichtfelder sichtbar mit `*`
- Labels stehen direkt oberhalb des Eingabefelds
- sichtbare Labels sind fachliche Begriffe, technische IDs bleiben unsichtbar

Standard-Verhalten:

- Tab-Reihenfolge von oben nach unten
- Enter = Speichern
- Esc = Abbrechen
- keine Tabellenbearbeitung durch Lehrkraefte
- UserForms sammeln nur Eingaben und rufen spaeter freigegebene Services auf
- keine Businesslogik in UserForms
- kein direkter Schreibzugriff auf Workbook-Tabellen
- nach erfolgreichem Speichern schliesst sich die UserForm
- danach wird die betroffene Ansicht aktualisiert

Standard-Buttons:

- Standardbuttons: Abbrechen und Speichern
- Abbrechen links, Speichern rechts
- primaere Aktion rechts unten
- Abbrechen links neben Speichern

Layout-Regeln:

- ruhige Abstaende
- keine ueberladene Informationsdichte
- Dokumentbereiche als einfache Listen mit klarer Hinzufuegen-Aktion

Experimenteller Referenzdialog `frm_student_new`:

- Zweck: neuen Schueler anlegen
- Rolle: verworfener UserForm-Versuch fuer Feature 1
- Status: deprecated, nicht produktiv freigegeben
- Felder: Vorname *, Nachname *, Stammgruppe *, Kurs *, Notiz
- keine Speicherlogik
- keine StudentService-Anbindung
- kein Tabellenzugriff

Referenzskizze fuer `dlg_neuer_schueler`:

```text
+--------------------------------------------+
|              Neuer Schueler                |
+--------------------------------------------+
| Vorname *                                  |
| [__________________________]               |
|                                            |
| Nachname *                                 |
| [__________________________]               |
|                                            |
| Stammgruppe *                              |
| [v Eulen]                                  |
|                                            |
| Kurs *                                     |
| [v Kurs 2]                                 |
|                                            |
| Notiz                                      |
| +--------------------------------------+   |
| |                                      |   |
| +--------------------------------------+   |
|                                            |
| Dokumente                                  |
| [Dokument] Foerderplan.pdf                 |
| [Dokument] Hoergeraetebericht.pdf          |
| [+ Dokument hinzufuegen]                   |
|                                            |
|          [Abbrechen]   [Speichern]         |
+--------------------------------------------+
```

## Stammgruppenübersicht

Die sichtbare Startansicht heißt `Stammgruppenübersicht`.

Die Schülerkarten der Stammgruppenübersicht zeigen den Kurs des Schülers. Die Stammgruppe wird dort nicht erneut auf jeder Karte angezeigt, weil die Ansicht bereits genau eine Stammgruppe darstellt.

Die Kartenfarbe wird aus der Kurszuordnung abgeleitet. Die konkrete Farbwelt bleibt Teil des freigegebenen Grunddesigns.

## Berichtfinalisierung und historische Revisionen

Die Berichtswerkstatt verwendet `PageHeader`, `SegmentedControl`, `SectionHeader`, `AppCard`, `StatusBadge`, `InlineMessage`, `EmptyState`, `Toast` und zentrale Buttonrollen. Der Kopf verbindet Kind- und Berichtskontext mit einem kompakten Statusbadge. `Entwurf` verwendet einen ruhigen Info-Ton, `Entwurf geändert` einen zurueckhaltenden Warnhinweis und `Finalisiert · Revision X` den positiven Statuston ohne Erfolgsinszenierung.

Die lokale Pilotnavigation ordnet `Auswählen`, `Schreiben` und
`Prüfen & finalisieren` als drei menschliche Aufgaben unterhalb des
Berichtskontexts. Fachlisten sind jeweils nur lokale Untergliederungen des
Schreib- beziehungsweise Auswahlbereichs. Auswahl und Schreiben bleiben frei
wechselbar. Die dauerhaft sichtbare untere Aktionsleiste enthaelt genau eine
primaere Draftaktion. Die mehrseitige Vorschau liegt als zentrale Prüffläche
des dritten Schritts auf einer neutralen Dokumentflaeche und nennt immer ihre
Draftquelle. Die read-only Revisionshistorie ist dort ausschließlich als
sekundäre Aktion `Frühere Fassungen` erreichbar.

Ein neuer Bericht aktiviert zunächst `Auswählen`. Die lokale Fachliste trennt ruhig
`Fächer des Kindes`, `Weitere Fächer` und – nur bei geöffnetem Bestand –
`Gespeicherte Fachabschnitte`. Eine dauerhaft sichtbare Textzeile nennt die
aktuell ausgewählten Fachnamen. Der Übergang `Weiter zum Schreibbereich`
bleibt bis zur ersten bewussten Auswahl deaktiviert. Überfachliche Domänen
werden nicht als reguläre weitere Berichtsfächer gestaltet.

Innerhalb eines Berichtfachs gliedert der Kompetenzbaum ruhig in `Mit Belegen
im Berichtszeitraum`, `Weitere auswählbare Kompetenzen` und historische
Referenzen. Die Beleggruppe steht zuerst und kennzeichnet ihre Kompetenzzeilen
zusätzlich textlich. Größe, Farbe und Position erzeugen keine Stärke-,
Schwäche- oder Empfehlungsaussage. Leere Gruppen entfallen; kanonische
Kompetenzbereich-/Thema-/Kompetenzreihenfolge und bewusste Checkboxauswahl
bleiben innerhalb jeder sichtbaren Gruppe erhalten.

Genau ein Bereich verwendet die zentrale helle Blue-Auswahlflaeche, kraeftigere
Typografie, Rahmen und den vorhandenen Auswahlindikator des `SegmentedControl`.
Inaktive Bereiche bleiben neutral; Hover, Fokus und Disabled-State stammen aus
der zentralen Komponentenbibliothek. Der orange Berichtskontext bleibt im Kopf
sichtbar, ist aber kein Navigations- oder Statuszustand.

Die direkt zugehörigen Seitenleisten verwenden normale Abschnittsüberschriften
und umbrechende Hilfetexte als Text. Nur auswählbare Fächer und Navigation sind
Buttons; nur echte Zustände dürfen `StatusBadge` verwenden. Statische Hinweise
werden nicht als Chip oder verschachtelte Meldungskarte dargestellt. Es gibt
keine Drop-Shadows, `QGraphicsOpacityEffect`, Höhenanimation oder andere
layoutverändernde Motion.

`Entwurf speichern` bleibt die primaere Draftaktion. `Bericht finalisieren` beziehungsweise `Neue Revision finalisieren` steht raeumlich getrennt im Finalisierungsstatus und verwendet eine serioese sekundaere Aktion. Erst der Bestaetigungsdialog verwendet fuer die explizite irreversible Bestaetigung die primaere Buttonrolle. Irreversibilitaet wird durch Text und erforderliche Checkbox vermittelt, nicht durch aggressive rote Gestaltung.

Revisionszeilen sind ruhige nicht-interaktive Karten mit Statusbadge und genau einer Aktion `Öffnen`. Technische `RPV`-ID und Snapshot-Hash erscheinen nur im Tooltip. Die finale Revisionsansicht verwendet eine zentrierte Papierflaeche mit Labels und Lesekarten; keine Eingabefelder, Bearbeiten-, Loeschen-, Entsperr- oder Wiederherstellungsaktion. Sprint 9A ergaenzt ausschliesslich fuer die aktuelle `finalized`-Revision die serioese sekundaere Aktion `Finales PDF erstellen`. Ein vorhandenes Artefakt wechselt dieselbe Aktion zu `Finales PDF anzeigen` und öffnet die gemeinsame schreibgeschützte In-Memory-Ansicht mit Mehrseiten-Scrollen, Zoom und Schließen. Render-, Lese- oder Integritaetsfehler erscheinen verständlich ohne technische Details. Ersetzte Revisionen bieten keine neue PDF-Erzeugung. Bestehende zentrale Motion-Regeln gelten unveraendert; Reduced Motion setzt Segment-, Toast- und Inline-Endzustaende unmittelbar.

Finale Bericht-/LEG-Tabellen verwenden umbruchfähige Zellen, variable
Zeilenhöhen und auf Folgeseiten wiederholte Tabellenköpfe. Die
LEG-Kompetenztabelle reserviert für `Fach` 24 Prozent der verfügbaren
Tabellenbreite; typische, lange und überfachliche Bezeichnungen bleiben mit
Innenabstand vollständig sichtbar. Diese Ausgaberegel verändert weder den
sicheren Viewer noch den RPA-/LCA-Artefaktvertrag.

## LEG-Abschluss und historische Revisionen

Der LEG-Workspace behaelt `Entwurf speichern` als einzige primaere Arbeitsaktion. `Gespräch abschließen` steht getrennt als serioese sekundaere Aktion im Abschlussbereich und ist bei ungespeicherten Widgetaenderungen deaktiviert. Eine kurze Bestaetigung macht deutlich, dass ein unveraenderlicher Abschlussstand entsteht, der Draft aber fuer spaetere Korrekturen bearbeitbar bleibt.

Der Status unterscheidet ruhig zwischen `Noch nicht abgeschlossen`, `Abgeschlossen · Revision X` und `Entwurf seit Abschluss geändert`. Revisionszeilen zeigen Nummer, Abschlussdatum, verantwortliche Lehrkraft und Status mit genau einer Aktion `Öffnen`. Die historische Ansicht verwendet Lesekarten ohne Eingabefelder sowie ohne Bearbeiten-, Loeschen-, Entsperr- oder Archivaktion. Technische IDs und Hashes bleiben sekundaere Integritaetsinformationen. Sprint 10B ergaenzt ausschliesslich fuer die aktuelle `completed`-Revision die serioese sekundaere Aktion `Finales PDF erstellen`. Ein vorhandenes Artefakt wechselt zu `Finales PDF anzeigen` und verwendet exakt dieselbe schreibgeschützte In-Memory-Ansicht wie Bericht-PDFs; `superseded`-Revisionen bieten keine neue PDF-Erzeugung.

## Überfachliche Kompetenzdarstellung

Gemeinsame Kompetenzlisten beginnen mit der ruhigen Abschnittsüberschrift
`Überfachliche Entwicklung` und den direkt bedienbaren Domänen `Selbst- und
Sozialkompetenz` sowie `Arbeits-/Lernkompetenz`. Danach folgt mit sichtbarem,
aber zurückhaltendem Abstand `Fächer` in kanonischer Quellenreihenfolge. Die
Überschriften sind keine Auswahlziele und erzeugen keine zusätzliche
Disclosure- oder Klickebene. Domänenkarten behalten dieselbe neutrale Form;
Farbe, Größe oder Position dürfen keine Leistungs- oder Prioritätsaussage
transportieren.

## Einklappbare Berichtsvorschau (07.09.2026)

Fachseiten der Entwurfsvorschau erhalten oberhalb der Papierseite eine ruhige native Schaltfläche mit Fachname, Pfeil und eindeutiger Aktion. Anfangs sind alle Abschnitte offen. Der geschlossene Abschnitt benötigt nur seine Schaltflächenhöhe; Inhalt und Papiergestaltung bleiben unverändert.

## Dezenter Sicherungshinweis (07.09.2026)

Sicherungshinweise verwenden eine ruhige Inline-Infomeldung im bestehenden Backupbereich und einen kurzen Status in seiner Navigationskarte. Kein Popup, Alarm, Rot, Countdown oder Blockieren der Arbeit. Die vorhandene bewusste Aktion `Backup erstellen` bleibt das einzige Erstellungsziel.

Die Kontextspalte im Beobachtungsdialog reserviert auch ohne Fokus auf der
Fachauswahl ausreichend Platz für vollständige Fachnamen, Marker und Pfeil.
Der Initialfokus in der Suche darf die Lesbarkeit bei 1180 × 760, 1280 × 800
und 1400 × 900 nicht verschlechtern; die vorhandenen drei Bereiche bleiben.


## Kompetenzübersicht als PDF – PO-Freigabe 11.10.2026

Freigegebene Ausnahme ausschließlich im Kompetenz-PDF: vier Originalpflanzen in schwarz/weiß statt sichtbarer Ratingtokens, mit Originalerklärungen für Standardfächer. Für soziale/Sport-Profile bleiben deren kanonische Texte in der Legende erhalten. Marineblau #123F67, Petrol #087F83 und weiche neutrale Tabellenflächen folgen der App. Balken hat vier diskrete Segmente, benannte Quelle/Bestätigungsdatum und Marker; keine Prozentzahl. A4, Fach beginnt auf neuer Seite, umbrochene Texte, wiederholte Spaltenköpfe und Seitenzählung. Fehlender Stand ist kein niedrigster Wert. Pflanzen gelten ausschließlich für diesen freigegebenen Export, nicht als neues App-Ratingprofil.
