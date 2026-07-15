# Schülerprofil – Ist-Analyse und verbindliche UX-Richtung

Stand: 14.07.2026

Status: Analyse und isolierter UX-Prototyp. Keine produktive Umsetzung.

## 0. Bestätigte Variante A und Orientierungskarte

Die Informationsarchitektur von Variante A ist bestätigt und bleibt unverändert: Profilkopf, lokale Tabs, die drei Hauptkarten Orientierungskarte, `Kompetenzen` und `Noch nicht dokumentiert`, anschließend neueste Beobachtungen und der kompakte Dokumentbereich. Variante B bleibt unveränderte Vergleichsreferenz.

Die Übersicht verwendet kein gemeinsames Kompetenz- oder Themendiagramm mehr. Sie funktioniert als Orientierungskarte für erkennbare Kompetenzänderungen und wählt fach- und themenübergreifend höchstens drei konkrete Kompetenzen aus, bei denen über mindestens zwei reale Ereignisse tatsächlich unterschiedliche dokumentierte Stände vorliegen. Fach- und Themenchips steuern die Orientierungskarte nicht. Die Hierarchie `Fach → Kompetenzbereich → Thema → Kompetenz` bleibt in den Daten und im Badge `Fach · Thema` nachvollziehbar.

### Verbindliche Auswahl- und Darstellungsregel

- Die statischen Ereignisse tragen Datum, Fach, Kompetenzbereich, Thema, stabile Kompetenz-ID, Kompetenztext, vorhandenen Status und Herkunft `Beobachtung` oder `Bestätigung`.
- Eine Kompetenz qualifiziert sich nur mit mindestens zwei realen Ereignissen und mindestens einem tatsächlichen dokumentierten Statuswechsel zwischen aufeinanderfolgenden Ereignissen.
- Die Übersicht zeigt höchstens drei qualifizierte Kompetenzen. Sortiert wird nach dem Datum der jüngsten tatsächlichen Statusänderung absteigend, bei Gleichstand nach curricularer Reihenfolge.
- Jede angezeigte Änderung bleibt mit den auslösenden beziehungsweise belegenden dokumentierten Ereignissen verknüpft. Die zeitliche Verbindung kodiert nur die Abfolge zwischen realen Ereignissen; sie ist kein berechneter kontinuierlicher Verlauf und keine Status-, Stufen- oder Trendlinie.
- Kurzbezeichnung, `Fach · Thema`, früherer und neuer dokumentierter Status sowie Zeitraum bilden die gleichwertige Textzusammenfassung.
- Alle Kompetenzen sind gleichgewichtet. Mehr Beobachtungen erhöhen keinen Status; eine Beobachtung ersetzt nicht automatisch eine Bestätigung.
- Mehrere Ereignisse mit unverändertem Status, ein einzelnes Ereignis und vollständig fehlende Ereignisse qualifizieren sich nicht. Fehlende Dokumentation bleibt ausschließlich in der separaten Karte `Noch nicht dokumentiert` sichtbar.
- Historische Referenzen bleiben als hohle Markierung und im Tooltip sichtbar. Sie werden nicht für neue Auswahl reaktiviert.

Verwendet werden ausschließlich die vorhandenen Statusstufen `-- Unterstützungsbedarf`, `- in Entwicklung`, `+ erreicht` und `++ sicher erreicht`. Die Übersicht zeigt dokumentierte Ereignisse und eine rein regelbasierte Auswahl nach tatsächlichem Statuswechsel. Sie zeigt keine Scores, Prozentwerte, Noten, Fachleistung, Rankings, Mittelwerte, Lerngeschwindigkeiten oder automatisch formulierte pädagogische Interpretation. Fehlende Dokumentation erzeugt keinen negativen Status.

### Gezielter UI-Feinschliff

- Der kompakte Profilkopf nutzt einen größeren Avatar, stärkeren Namen, Chips für Stammgruppe/Kurse und einen kleinen Ring mit der Beschriftung `Dokumentiert` sowie `16 / 21`.
- Der Ring visualisiert ausschließlich Dokumentationsumfang. Er enthält keine Prozentzahl, Ampelfarbe oder Leistungssemantik.
- Zwei Kompetenzkartenstudien sind umschaltbar: `Ring` und `Leisten`. Die Ringvariante ist gewählt, weil sie ruhiger ist und die drei Hauptkarten weniger visuell konkurrieren lässt.
- Der Dokumentbereich verwendet flache, kompakte Zeilen mit kurzem Status und klarer Aktion.
- Bei neuesten Beobachtungen steht die konkrete Kompetenz vor Fach/Datum, Notiz und Kontext.
- Mathematik verwendet Blau, Deutsch Violett und Sachunterricht Ocker zur Orientierung. Kreis und Quadrat unterscheiden Beobachtung und Bestätigung zusätzlich zur Farbe; historische Ereignisse sind hohl. Es gibt keine Rot-Grün-Logik und keine technische ID in der Oberfläche.

## 1. Geprüfte Dateien, Klassen, Funktionen und Tests

### Produktiver Profilpfad

- `src/desktop_app/screens/student_profile_screen.py`
  - `StudentProfileScreen`
  - Aufbau und lokale Navigation: `_build()`, `_select_profile_section()`, `_sync_profile_navigation()`, `_update_profile_header_context()`, `_scrollable_tab()`
  - Überblick: `_overview_tab()`, `_basis_data_card()`, `_overview_summary_card()`, `_render_profile_overview()`, `_render_overview_recent_observations()`, `_render_overview_documentation()`, `_render_overview_development()`
  - Beobachtungen: `set_observations()`, `apply_observation_filters()`, `_filtered_observations()`, `_observation_card()`, `_observation_summary()`, `_observation_actions()`, `_observation_attachments_block()`
  - Kompetenz-Cockpit: `set_competency_cockpit()`, `apply_competency_cockpit_filters()`, `_cockpit_subject_card()`, `_cockpit_learning_area_card()`, `_cockpit_topic_card()`, `_cockpit_competency_details()`, `_add_competency_confirmation_block()`, `_add_competency_proposal_block()`, `_add_competency_evidence_block()`, `_historical_competency_section()`
  - Bericht und Dokumente: `set_report_preview()`, `_report_subject_card()`, `report_text()`, `copy_report_text_to_clipboard()`, `export_report_text()`, `set_documents()`, `_document_row()`
  - Zustandsbestandsschutz: `set_student()`, `_capture_profile_scroll_positions()`, `_restore_profile_scroll_positions()`
- `src/desktop_app/view_models/student_view_model.py`
  - `StudentDetailViewModel`, `StudentDocumentationSummaryViewModel`, `StudentProfileOverviewViewModel`, `StudentDocumentViewModel`
  - `build_student_profile_overview()`, `documentation_summary_from_subjects()`
  - `_overview_strengths()`, `_overview_watch_items()`, `_overview_development_items()`, `_overview_reliability_hint()`
  - ältere Live-Berichtsvorschau: `StudentReportPreviewViewModel` und `format_student_report_preview_text()`
- `src/desktop_app/view_models/observation_view_model.py`
  - `ObservationListItem`, `ObservationRatingViewModel`
  - kanonischer Kompetenzstatus: `StudentCompetencyStatusViewModel`, `StudentCompetencyEvidenceViewModel`
  - Cockpit-Projektion: `StudentCompetencyCockpitViewModel` samt Fach-, Lernbereichs- und Themenprojektionen sowie `build_student_competency_cockpit()`
  - Dokumentationsprojektion: `StudentDocumentationSubjectStatus`, `StudentDocumentationLearningAreaStatus`
- `src/desktop_app/adapters/student_desktop_adapter.py`
  - Stammdaten: `get_student_profile()`
  - Beobachtungen und Dateien: `list_observations_for_student()`, `list_documents_for_student()`
  - kanonischer Status: `list_competency_status_projection_for_student()`, `competency_cockpit_for_student()`, `list_documentation_status_for_student()`
  - ältere Live-Berichtsvorbereitung: `get_report_preview_for_student()`
  - produktiver Bericht: `list_learning_report_drafts_for_student()`, `learning_report_revision_status()`, `load_learning_report_revision()`
  - produktives LEG: `list_learning_conference_drafts_for_student()`, `learning_conference_preparation_for_student()`
  - zentrale Fachableitung bleibt in `_competency_status_view_model()` und nicht im Screen.
- `src/desktop_app/shell.py`
  - Profilzusammenstellung: `AppShell.show_student_profile()`
  - Berichtseinstieg und Revisionen: `open_learning_report_dialog()`
  - LEG-Einstieg und Mehrfach-Draft-Auswahl: `open_learning_conference_dialog()`
  - bestehende Beobachtungs-, Datei-, Edit- und Soft-Delete-Wege
- `src/desktop_app/navigation.py`
  - global nur `Heute`, `Schüler`, `Stammdaten`, `Einstellungen`
  - das Profil bleibt kindbezogener lokaler Arbeitsraum und wird nicht neues globales Navigationsziel.

### Produktive Referenzsprache

- Dashboard: `src/desktop_app/screens/overview_screen.py`, insbesondere `OverviewScreen`, `_render_hero()`, `_render_today()`, `_render_matching_children()` und `_render_heatmap()`
- Bericht: `src/desktop_app/dialogs/learning_report_dialog.py` und `src/desktop_app/view_models/learning_report_view_model.py`
- LEG: `src/desktop_app/dialogs/learning_conference_dialog.py` und `src/desktop_app/view_models/learning_conference_view_model.py`
- freigegebene isolierte UX-Referenzen:
  - `prototypes/learning_report_ux/`
  - `prototypes/learning_conference_ux/`
- gemeinsame Komponenten und Verhalten: `src/desktop_app/components.py`, `src/desktop_app/theme.py`, `src/desktop_app/motion.py`

### Verbindliche Dokumentation

- `docs/PROJECT_CONSTITUTION.md`
- `docs/TECHNICAL_NAMES.md`
- `docs/DATA_REGISTRY.md`
- `docs/UI_DATA_MAPPING.md`
- `docs/VIEW_DATA_OWNERSHIP.md`
- `docs/DATA_LIFECYCLE.md`
- `docs/DESIGN_SYSTEM.md`
- `UX_BLUEPRINT.md`

### Zugehörige Tests und gesicherte Verträge

Die vollständigen profilbezogenen Bereiche in `tests/test_desktop_app_adapter.py` sowie die vollständigen Bericht-, Revisions- und LEG-UI-Suiten wurden geprüft. Besonders bindend sind:

- Profilkopf und Startzustand:
  - `test_selected_student_creates_profile_view_model`
  - `test_student_profile_view_model_contains_header_and_basis_data`
  - `test_student_profile_opens_with_overview_tab`
  - `test_student_profile_keeps_child_and_current_section_visible`
  - `test_student_profile_navigation_is_keyboard_reachable_and_complete`
- Beobachtungsverlauf:
  - `test_student_profile_observation_cards_offer_edit_and_delete`
  - `test_student_profile_observation_cards_render_compact_summary`
  - `test_student_profile_observation_details_can_be_expanded`
  - Filter-, Suche-, Limit-, Reset-, Empty-State-, Anhang- und Shell-Refresh-Tests
- Überblick:
  - `test_student_profile_overview_summarizes_documented_student`
  - `test_student_profile_overview_does_not_invent_strengths_without_data`
  - `test_student_profile_overview_view_model_uses_existing_data_only`
  - `test_student_profile_overview_watch_items_use_documentation_subjects`
- Kompetenz-Cockpit:
  - `test_student_profile_cockpit_has_no_confirmation_mutation_actions`
  - `test_competency_cockpit_projects_subject_area_topic_and_progress`
  - alle Filter-, Hierarchie-, Empty-State-, Historien-, Evidenz-, Navigations- und Zustands­erhalt-Tests
  - `test_competency_detail_keeps_confirmation_and_proposal_separate`
  - `test_student_profile_cockpit_separates_legacy_section`
  - `test_competency_cockpit_does_not_recalculate_status_in_screen`
- Responsive, Fokus und Motion:
  - `test_student_profile_resizes_without_losing_navigation_or_primary_action`
  - `test_disclosure_reduced_motion_and_fast_switches_end_in_correct_state`
  - `test_profile_refresh_keeps_observation_filters_and_scroll_state`
- Bericht:
  - `tests/test_learning_report.py`, insbesondere Profileinstieg, vier lokale Arbeitsbereiche, bewusste Auswahl, historische Referenzen, Entwurfskennzeichnung und Output-Abgrenzung
  - `tests/test_report_revision_ui.py`, insbesondere `Entwurf`, `Entwurf geändert`, `Finalisiert · Revision X`, neueste Revision zuerst und snapshotbasierte schreibgeschützte Ansicht
- LEG:
  - `tests/test_learning_conference_ui.py`, insbesondere Profileinstieg, einzelne/mehrere Drafts, sechs Phasen, neutrale Zustände, historische Belege, Dirty-State, Tastaturbedienung, Reduced Motion und Zielgrößen
- Persistenz-/Lifecycle-Regressionen:
  - `tests/test_report_draft.py`
  - `tests/test_report_finalization.py`
  - `tests/test_learning_conference_draft.py`

Am Prototyp wurden keine produktiven Tests verändert.

## 2. Bestehende Funktionen, die erhalten bleiben müssen

1. Profilöffnung ausschließlich über `student_id`; Name ist Anzeige, keine technische Identität.
2. Rückkehr zur vorherigen Schülerauswahl und Erhalt des bestehenden Shell-Flows.
3. Dauerhaft sichtbarer Kindkontext mit Name, Stammgruppe und Kurs.
4. Genau eine dominante Profilaktion für die zentrale Beobachtungserfassung.
5. Derselbe produktive Beobachtungsdialog aus Profil, Schülerliste und Dashboard.
6. Beobachtungen neueste zuerst, zunächst kompakt begrenzt, mit Suche, Fach- und Bewertungsfilter.
7. Beobachtungsdetails, Anhänge, Bearbeiten und Soft Delete über bestehende IDs und Shell-Wege.
8. Kompetenz-Cockpit ausschließlich aus der kanonischen Statusprojektion; keine Statusneuberechnung im Screen.
9. Fach → Kompetenzbereich → Thema → konkrete Kompetenz einschließlich bestehender Filter und Klassenstufenansichten.
10. Strikte Trennung von bestätigtem Stand, Vorschlag aus Beobachtungen und Beobachtungsevidenz.
11. Historische Kompetenzen und fehlende Katalogreferenzen als separater Lesekontext.
12. Navigation aus Kompetenzbelegen in die vorhandene Beobachtung und in deren Bearbeitung.
13. Berichtsentwurf, finale Revisionen und LEG als getrennte fachliche Wege.
14. Finale Berichtrevision ausschließlich snapshotbasiert und schreibgeschützt.
15. Dateien studentenzentriert, Öffnen über Betriebssystem, Entfernen als Soft Delete.
16. Refresh desselben Kindes erhält lokalen Reiter, Filter, Disclosures und Scrollposition; Kindwechsel setzt lokalen Zustand zurück.
17. Reduced Motion, sichtbarer Fokus, tastaturfähige lokale Navigation und kein horizontaler Gesamtscroll bei 1180 × 760.

## 3. Konkrete UX-Probleme des aktuellen Screens

### Zu hohe lineare Dichte

Der Überblick stapelt `Basisdaten`, `Halbjahresblick`, `Entwicklung`, `Letzte Beobachtungen` und `Dokumentationsstand` vertikal. Jeder Block erhält nahezu dasselbe visuelle Gewicht. Eine Lehrkraft muss lesen, bevor sie priorisieren kann.

### Wiederholter Kindkontext

Stammgruppe und Kurs stehen bereits im Profilkopf und werden in `Basisdaten` erneut angezeigt. Die Schülernotiz wird dadurch zusammen mit bereits bekanntem Kontext zu einer weiteren großen Karte.

### Automatisch interpretierende Sprache im Überblick

`build_student_profile_overview()` leitet über `_overview_strengths()`, `_overview_watch_items()` und `_overview_development_items()` aus Ratings und Historien die Bereiche `Stärken`, `Im Blick behalten` und `Entwicklung` ab. Das ist zwar bestehender Code, wirkt aber pädagogisch stärker interpretierend als die kanonischen Fakten. Formulierungen wie `positive Entwicklung erkennbar` in der älteren Berichtsvorbereitung verstärken dieses Risiko.

Für das neue Zielbild werden solche Aussagen nicht in die erste Bildschirmhöhe übernommen. Sichtbar bleiben datierte Beobachtungen, Dokumentationsumfang, bestätigte Stände und ausdrücklich ausgewählte konkrete Verläufe.

### Zu viele Informationen pro Kompetenzkarte

Eine geöffnete Kompetenz kann gleichzeitig Volltext, Dokumentationszustand, bestätigten Stand, Bestätigungsdatum, Bestätigungsnotiz, neuere Beobachtungen, Beobachtungsvorschlag und mehrere Evidenzkarten zeigen. Fach-, Bereichs- und Themenkarten wiederholen zusätzlich Counts, Balken und Öffnen-Texte.

### Berichtsfunktion doppelt und veraltet im Profil

Der lokale Bereich `Bericht` zeigt eine ältere Live-Berichtsvorschau mit automatisch gruppierten Bereichen `Aktueller Stand`, `Stärken`, `Entwicklung`, `Unterstützungsbedarf` und Beispielbeobachtungen. Parallel existiert die produktive Berichtswerkstatt mit Draft, Finalisierung und Revisionen. Dadurch konkurrieren zwei Berichtseinstiege und zwei Darstellungslogiken.

### Bericht, Revisionen und LEG sind im Profil nicht als Status lesbar

Der Profilkopf versteckt Bericht und LEG im Menü `Weitere Aktionen`. Der lokale Berichtstab kennt den produktiven Draft-/Revisionsstatus nicht. Innerhalb von fünf Sekunden ist deshalb nicht erkennbar, ob ein Berichtsentwurf, finale Revisionen oder ein LEG-Entwurf vorhanden sind.

### Filter beanspruchen viel Breite

Beobachtungs- und Kompetenzfilter liegen jeweils vollständig horizontal. Das funktioniert nach aktuellem Testvertrag, wird bei 1180 Pixeln aber schnell dicht und erschwert eine spätere Seitenleiste.

### Teilweise mauszentrierte Karteninteraktion

`_make_clickable_card()` setzt Mauszeiger und `mouseReleaseEvent`, macht die Karte selbst aber nicht zu einem tastaturaktivierbaren Control. Die enthaltenen Buttons sind erreichbar, die zusätzliche Karten-Klickfläche jedoch nicht gleichwertig per Tastatur.

### Keine visuelle zeitliche Orientierung

Ratinghistorien liegen bereits als datierte Evidenz vor, erscheinen aber überwiegend als Text, Pfeilkette oder tief in Kompetenzdetails. Der beigefügte Referenzscreen zeigt überzeugend, dass eine kompakte Zeitdarstellung den Dashboardcharakter und die schnelle Orientierung deutlich verbessert.

## 4. Rollenbasierte Analyse

### A. Lehrkraft im Unterrichtsalltag

Innerhalb von fünf Sekunden müssen erkennbar sein:

- das richtige Kind, Stammgruppe und Kurse
- die Hauptaktion `Beobachtung erfassen`
- ob und wie aktuell dokumentiert wurde
- die neuesten ein bis drei Beobachtungen
- welche Lernbereiche noch keine Dokumentation besitzen
- ob Berichtsentwurf, finale Revisionen oder LEG-Entwurf vorliegen

Der häufigste Weg bleibt `Beobachtung erfassen`. Beim schnellen Kindwechsel stören lange Textkarten, wiederholte Basisdaten und ein Überblick, der pädagogische Interpretation vor Fakten setzt. Kompetenzvolltexte, Belegverläufe, Dateimetadaten und Revisionsdetails gehören in vertiefte Bereiche.

### B. Pädagogische Fachlichkeit

Unterstützend sind datierte Einzelbeobachtungen, konkreter Kompetenzbezug, getrennte Bestätigung und Beobachtungsvorschlag sowie sichtbare Datenlücken. Kritisch sind Prozentkreise, Fachmittelwerte, Rankingfarben und automatisch behauptete Stärken oder Trends.

Neutrale Formulierungen:

- `16 von 21 Lernbereichen mit vorhandener Dokumentation`
- `5 Lernbereiche noch nicht dokumentiert`
- `Bestätigter Stand vorhanden`
- `Neue Beobachtungen seit der Bestätigung`
- `Noch keine aktiven Beobachtungen dokumentiert`
- `Historische Kompetenzreferenz`
- `Beobachtungsbeleg nicht mehr verfügbar`

Nicht verkürzt werden dürfen die konkrete Kompetenz, die Trennung von Bestätigung und Beobachtung, historische Kennzeichnungen, fehlende Referenzen und die Tatsache, dass Dokumentationsabdeckung keine Leistung ist.

### C. UX und Informationsarchitektur

In den Profilkopf gehören nur Kind, Stammgruppe, Kurse, ein kompakter Dokumentationshinweis, Rückweg und Hauptaktion. Die erste Bildschirmhöhe erhält eine Dashboardstruktur aus ausgewähltem Kompetenzverlauf, Dokumentationsüberblick, offenen Dokumentationsbereichen, neuesten Beobachtungen und Dokumentstatus.

Progressive Disclosure ist sinnvoll für:

- Kompetenzvolltexte und Evidenz
- Beobachtungsnotiz, Kompetenzbewertungen und Anhänge
- Revisionshistorie
- historische Kompetenzen und nicht verfügbare Referenzen
- vollständige Datei- und Dokumentlisten

Primäraktion: `Beobachtung erfassen`.

Sekundäraktionen: Kompetenz-Cockpit öffnen, alle Beobachtungen, Bericht öffnen/erstellen, LEG öffnen/vorbereiten, Datei hinzufügen, Revision öffnen, Schüler bearbeiten.

### D. Accessibility und Bedienbarkeit

Zielvertrag:

- Tab-Reihenfolge: Rückweg → Profilaktionen → lokale Navigation → sichtbarer Bereich von oben links nach unten rechts.
- alle Kartenaktionen als echte Buttons; keine ausschließlich mausaktive Karte
- sichtbarer 2-Pixel-Fokus mit ausreichendem Kontrast
- Mindesthöhe interaktiver Controls etwa 36 Pixel
- keine Information ausschließlich über Farbe; Badges tragen Text
- lokale horizontale Navigation mit Links/Rechts; vertikale Variante mit Hoch/Runter sowie Home/End bei produktiver Übertragung
- Orientierungskarte braucht einen zugänglichen Namen und eine gleichwertige textliche Zusammenfassung der dokumentierten Änderungen
- Reduced Motion zeigt alle Endzustände sofort; keine Höhen-, Geometrie- oder Screenanimationen
- bei 1180 × 760 genau ein dominanter vertikaler Scrollbereich und kein horizontaler Gesamtscroll

Der isolierte Prototyp verwendet keine Animationen, echte Buttons, sichtbare Fokuszustände, Accessible Names für Filter und Orientierungskarte sowie ausschließlich vertikales Scrollen.

### E. Architektur

Direkt wiederverwendbar:

- `StudentDetailViewModel`
- `ObservationListItem`
- `StudentCompetencyStatusViewModel` einschließlich datierter `evidence`
- `StudentCompetencyCockpitViewModel`
- `StudentDocumentationSubjectStatus`
- `StudentDocumentViewModel`
- `LearningReportRevisionStatusViewModel` aus dem produktiven Berichtspfad
- bestehende Report- und LEG-Draft-Listen aus dem Adapter

Für die spätere Umsetzung ist eine reine Profilübersichts-Komposition im Adapter-/ViewModel-Layer nötig. Sie soll vorhandene Projektionen zusammenführen, nicht Status neu berechnen. Vor der Benennung oder Implementierung muss sie in `TECHNICAL_NAMES`, `UI_DATA_MAPPING` und `VIEW_DATA_OWNERSHIP` registriert werden.

Die spätere Orientierungskarte kann datierte Ereignisse aus `StudentCompetencyStatusViewModel.evidence` verwenden. Sie benötigt zusätzlich stabile Zuordnung zu Fach, Kompetenzbereich, Thema und Kompetenz sowie die getrennte Herkunft Beobachtung/Bestätigung. Die UI darf Status nicht neu berechnen. Es entstehen keine Fachmittelwerte, Scores oder Trendtexte. Die ausführliche Entwicklung bleibt ein eigener Tab `Entwicklung`; für die produktive Projektion sind dessen Datenumfang und Stichtage noch offen.

`StudentProfileScreen` setzt derzeit zahlreiche sichtbare Texte selbst zusammen, unter anderem:

- Profiluntertitel in `_update_profile_header_context()`
- Überblickszeilen in `_render_profile_overview()` und `_render_overview_recent_observations()`
- Beobachtungssummary in `_observation_summary()`
- Kompetenz-Counts, Details und Statusblöcke
- Berichtsbuckets und Evidenzzeilen

Bei der produktiven Übertragung sollen kompakte, mehrfach verwendete Labels und Dokumentstatus aus displayfertigen ViewModels kommen. Reine Sichtbarkeit, Tabwahl, Filterung und Disclosure bleiben UI-State.

Der Prototyp ist vollständig getrennt: nur `PySide6`, `demo_data.py`, keine produktiven Imports, keine SQLite-/Repository-/Adapter-Anbindung und keine Navigationseinbindung.

## 5. Redundante oder zu textlastige Inhalte

| Aktuell | Problem | Zielrichtung |
| --- | --- | --- |
| Stammgruppe/Kurs im Kopf und erneut in `Basisdaten` | doppelt | nur im Kopf; Schülernotiz bei Bedarf separat |
| Halbjahresblick mit Count, letzter Beobachtung, Zuverlässigkeit, Stärken und Hinweisen | zu viele Rollen in einer Karte | neutrale Dashboardkarten; Interpretation nicht auf erster Ebene |
| `Letzte Beobachtungen` im Überblick plus vollständiger Beobachtungstab | doppelt, aber fachlich sinnvoll | Überblick auf 2–3 kompakte Karten begrenzen, vollständige Liste im Bereich |
| Dokumentationssummary plus Fachdetails plus Cockpit-Counts | mehrfach | Überblick nur Gesamtzahl und offene Fächer; Hierarchie im Cockpit |
| Fortschrittsbalken auf mehreren Cockpit-Ebenen | kann wie Leistung wirken | kurze Textcounts; Erläuterung nur einmal pro Bereich |
| Berichtstab mit Live-Vorschau plus produktive Berichtswerkstatt | widersprüchliche Berichtsbedeutung | Profil zeigt nur Einstieg und echten Draft-/Revisionsstatus |
| Bericht und LEG im Menü | Status unsichtbar | kompakter Dokumentbereich auf erster Bildschirmhöhe |
| Datei hinzufügen im Kopf und erneut im Dateibereich | doppelte Aktion | im Kopf untergeordnet; sichtbar im Dokumentbereich |
| Vollständige Kompetenz-/Bestätigungs-/Evidenztexte in einer Karte | überladen | dreistufige Disclosure: Count → Kompetenzzeile → vollständige Evidenz |

## 6. Zwei Layoutvarianten

### Variante A – Arbeitsprofil / Schülerdashboard (empfohlen)

Seitenstruktur:

1. kompakter Profilkopf
2. horizontale lokale Navigation
3. Dashboardzeile mit Orientierungskarte, Kompetenz-/Dokumentationsüberblick und `Noch nicht dokumentiert`
4. neueste Beobachtungen und Dokumentstatus
5. kontextueller Hinweis
6. vertiefte Bereiche für Kompetenzen, Beobachtungen, Dokumente und Verlauf

Erste sichtbare Bildschirmhöhe:

- Name, Stammgruppe, Kurse
- `Beobachtung erfassen`
- bis zu drei fach- und themenübergreifend erkennbare Kompetenzänderungen
- Dokumentationsabdeckung und offene Lernbereiche
- neueste Beobachtungen
- Bericht, Revisionen, LEG und Dateien

Karten und Hierarchie:

- genau eine große Orientierungskarte
- zwei schmalere Informationskarten
- eine breite Beobachtungsfläche
- ein kompakter Dokumentblock
- Details über klare Textaktionen

Verhalten bei kleineren Fenstern:

- dieselbe horizontale Navigation
- Karten bleiben innerhalb des vertikalen Scrollbereichs
- Texte umbrechen, Buttons bleiben sichtbar
- kein horizontaler Gesamtscroll

Vorteile:

- stärkster Dashboardcharakter
- schnellste Fünf-Sekunden-Orientierung
- visuell anschlussfähig an `Heute`, Bericht und LEG
- vorhandene lokale Navigation bleibt erhalten
- Kompetenz-Cockpit behält volle Inhaltsbreite
- geringe Navigations- und Migrationsrisiken

Nachteile:

- die erste Bildschirmhöhe zeigt mehrere Informationsrollen gleichzeitig
- die zeitliche Verbindung könnte ohne klare Textzusammenfassung als kontinuierlicher Verlauf missverstanden werden
- Dokumentstatus benötigt eine neue reine Profilkomposition

Fachliche Risiken:

- nur transparente Auswahl nach realem Statuswechsel, keine pädagogische Wichtigkeitsbewertung
- keine Fachmittelwerte oder mehrfarbigen Leistungsreihen
- offene Bereiche ausdrücklich als Dokumentationslücke, nicht als Defizit

Technische Auswirkungen:

- bestehender Profilkopf und Segmentvertrag können konzeptionell weiterverwendet werden
- bestehende kanonische Status- und Dokumentationsprojektionen reichen für Counts und konkrete Verlaufspunkte
- zusätzlicher aggregierter Read-Contract für Report-/Revisions-/LEG-Status nötig, ohne Schemaänderung

### Variante B – Fokusprofil mit lokaler Seitenleiste

Seitenstruktur:

1. kompakter Profilkopf
2. linke lokale Profilnavigation
3. ein dominanter rechter Arbeitsbereich
4. schmaler Dokument-/Offen-Kontext im Überblick

Erste sichtbare Bildschirmhöhe:

- Name und Hauptaktion
- dominanter konkreter Kompetenzverlauf
- offene Dokumentationsbereiche
- Bericht-/LEG-Kontext

Karten und Hierarchie:

- eine große Fokuskarte
- zwei untergeordnete Kontextkarten
- vertiefte Bereiche ersetzen den Fokusinhalt vollständig

Verhalten bei kleineren Fenstern:

- Seitenleiste bleibt etwa 214 Pixel breit
- Hauptbereich scrollt vertikal
- Filter können bei 1180 Pixeln umbrechen müssen
- Cockpit erhält weniger Breite

Vorteile:

- sehr klare Aufmerksamkeitsführung
- geeignet für längere Arbeit in genau einem Bereich
- Anlehnung an Bericht- und LEG-Workspaces mit lokaler Leiste

Nachteile:

- zusätzliche lokale Navigation konkurriert mit globaler Shell-Seitenleiste
- deutlich weniger Breite bei 1180 × 760
- langsamerer Wechsel zwischen Überblick und Detail
- wirkt stärker wie ein eigener Workflow als wie ein live Schülerdashboard

Fachliche Risiken:

- der dominante Verlauf kann zu viel Gewicht gegenüber Beobachtungsqualität und Dokumentstatus erhalten

Technische Auswirkungen:

- größerer Umbau des Screenlayouts
- zusätzliche Tastatur- und Zustandslogik für vertikale Navigation
- höhere Regressiongefahr für Cockpit, Filter und Scrollzustände

## 7. Begründete Empfehlung

Variante A ist die bevorzugte Richtung.

- Im Unterricht sind Kind, Hauptaktion, jüngste Beobachtungen und Dokumentationslücken schneller erfassbar.
- Die Textdichte sinkt, weil die erste Ebene Counts, kurze Metadaten und wenige Beobachtungssätze nutzt.
- Die Orientierungskarte vermittelt zeitliche Orientierung über höchstens drei dokumentierte Kompetenzänderungen, ohne ein gemeinsames Themen- oder Kompetenzdiagramm zu bilden.
- Die horizontale lokale Navigation schließt an den bestehenden Profilvertrag an und lässt dem Kompetenz-Cockpit mehr Breite.
- Bericht und LEG erscheinen als eigene Dokumentwege und werden nicht wieder in das Profil eingebaut.
- Bei 1180 × 760 bleibt nur ein dominanter vertikaler Scrollbereich; eine zweite Seitenleiste entfällt.
- Die Umsetzung kann screen- und projektionsnah erfolgen, ohne Schema, Statuslogik oder globale Navigation zu ändern.

## 8. Textuelle Wireframe-Spezifikation der bevorzugten Variante

### Profilkopf

- Inhalt: Rückweg, Name, Stammgruppe, Kurse, kompakter Dokumentationshinweis
- maximale Textmenge: eine Namenszeile, eine umbrechende Metazeile, ein Count-Badge
- sichtbare Metadaten: keine technischen IDs
- Aktion: `Beobachtung erfassen` primär; `Weitere Aktionen` quiet
- Interaktion: Hauptaktion öffnet vorhandenen zentralen Beobachtungsdialog
- Priorität: dauerhaft höchste
- 1400 × 900: eine Zeile unter dem Rückweg
- 1180 × 760: Metadaten dürfen umbrechen; Hauptaktion bleibt sichtbar

### Lokale Navigation

- Inhalt in Variante A: `Überblick`, `Kompetenzen`, `Beobachtungen`, `Dokumente`, `Entwicklung`; Variante B behält `Verlauf`
- maximale Textmenge: kurze Einzelwörter
- Aktion: rein lokaler Bereichswechsel
- Interaktion: Pfeiltasten zusätzlich zu Tab/Enter/Space
- Priorität: hoch
- beide Zielgrößen: vollständig sichtbar, kein horizontaler Scroll

### Erste Reihe – Orientierungskarte

- Inhalt: höchstens drei konkrete Kompetenzen mit mindestens zwei realen Ereignissen und mindestens einem dokumentierten Statuswechsel
- maximale Textmenge: je Zeile Kurzbezeichnung, `Fach · Thema`, früherer → neuer Status und Zeitraum
- sichtbare Metadaten: Fach, Thema, früherer und neuer dokumentierter Stand, Zeitraum und verknüpfte reale Belege
- Aktion: `Alle Entwicklungen ansehen`; im Prototyp nur flüchtiges Feedback
- Interaktion: reale Belege mit Maus und Tastatur prüfbar; unmittelbarer Zustandswechsel ohne Animation; keine Auswahl nach pädagogischer Wichtigkeit
- Priorität: hoch
- 1400 × 900: drei getrennte kompakte Zeilen nutzen die breite bestehende Hauptkarte, ohne überlagerte Datenreihen
- 1180 × 760: die Orientierungskarte nutzt die volle Breite; Metadaten bleiben innerhalb der Karte und alle weiteren Inhalte liegen im einzigen Seiten-Scrollbereich

### Erste Reihe – Kompetenzüberblick

- Inhalt: Lernbereiche mit Dokumentation, bestätigte und beobachtete Zustände als Counts
- maximale Textmenge: drei kurze Zeilen
- sichtbare Metadaten: Counts, keine Prozentwertung
- Aktion: `Kompetenz-Cockpit öffnen`
- Priorität: hoch
- beide Zielgrößen: kompakte mittlere Karte

### Erste Reihe – Noch nicht dokumentiert

- Inhalt: Gesamtzahl offener Lernbereiche und kurze Fachverteilung
- maximale Textmenge: höchstens vier Fächer direkt; weitere im Detail
- sichtbare Metadaten: Count je Fach
- Aktion: `Offene Bereiche ansehen`
- Priorität: hoch, aber neutral
- beide Zielgrößen: Warnfläche ohne Ampelfarbe; Hinweis `keine Aussage über Leistung`

### Beobachtungsbereich

- Inhalt: neueste drei Beobachtungen mit Datum, Fach, Notizvorschau, Kontext, Kompetenz- und Anhangszahl
- maximale Textmenge: maximal etwa zwei Notizzeilen pro Karte
- Aktion: `Alle anzeigen`; im Detail `Bearbeiten`, `Löschen`, Anhänge öffnen
- Interaktion: Details erst im Beobachtungsbereich
- Priorität: hoch
- 1400 × 900: drei kompakte Zeilen/Karten
- 1180 × 760: unter der ersten Reihe im Scrollbereich

### Dokumentenbereich

- Inhalt: Berichtsentwurf, aktuelle Revision und Revisionsanzahl, LEG-Entwurf, Dateizahl
- maximale Textmenge: eine Statuszeile pro Dokumentweg
- Aktion: `Öffnen`; im Detail Bericht erstellen/öffnen, LEG vorbereiten/öffnen, Revision öffnen, Datei hinzufügen
- Interaktion: keine Bericht- oder LEG-Bearbeitung im Profil selbst
- Priorität: mittel
- beide Zielgrößen: kompakter Block neben beziehungsweise unter Beobachtungen

### Kompetenzdetail

- Inhalt: bestehende Filter und vollständige Fachhierarchie
- maximale Textmenge: pro geschlossener Ebene Titel plus Count; Volltext erst an konkreter Kompetenz
- sichtbare Metadaten: Dokumentationszustand, bestätigter Stand, Vorschlag, Evidenz getrennt
- Aktion: Beobachtung öffnen/bearbeiten
- Interaktion: bestehende Filter bleiben rein visuell; Fortschritt bleibt kanonisch
- Priorität: vertiefter Arbeitsbereich
- beide Zielgrößen: volle Inhaltsbreite, ein vertikaler Scrollbereich

### Dokumentdetail und Verlauf

- Inhalt: echter Draftstatus, finale Revisionen neueste zuerst, LEG-Status, Dateien und getrennte Chronologien
- maximale Textmenge: eine Metazeile pro Zeile; Details nach Öffnen
- sichtbare Metadaten: Datum, Lehrkraft-Anzeigename, `Aktuell`/`Ersetzt`, `Entwurf`/`Entwurf geändert`
- Aktion: ausschließlich vorhandene fachliche Wege
- Priorität: vertieft
- historische Referenzen: klar benannt, nie still entfernt oder reaktiviert

### Empty States

- keine Beobachtungen: `Noch keine Beobachtungen` plus genau `Beobachtung erfassen`
- wenig Dokumentation: neutraler Count, kein Warnurteil
- kein Bericht: `Noch kein Berichtsentwurf` plus `Bericht erstellen`
- keine Revision: `Noch keine finale Revision`
- kein LEG: `Noch kein LEG-Entwurf` plus `LEG vorbereiten`
- keine Dateien: `Noch keine Dateien hinterlegt` plus `Datei hinzufügen`
- Filter ohne Treffer: Filter ändern oder zurücksetzen; Datenzustand bleibt unangetastet

### Lade- und Fehlerzustände für die spätere Produktfassung

- Laden: vorhandene Kartengeometrie erhalten, ruhige textliche Ladeanzeige; keine springenden Skeleton-Animationen
- fachlicher Leerzustand: kontextbezogene Aktion
- erwarteter Fehler: `InlineMessage` im betroffenen Bereich
- technischer Blocker: modaler Fehler nur wenn Fortsetzen nicht möglich ist
- fehlende historische Referenz: neutrale dauerhafte Hinweisfläche mit stabiler ID nur im Tooltip oder Detail

## 9. Prototypdateien und Startbefehl

- `prototypes/student_profile_ux/main.py`
- `prototypes/student_profile_ux/demo_data.py`
- `prototypes/student_profile_ux/README.md`
- `prototypes/student_profile_ux/ANALYSIS.md`
- `prototypes/student_profile_ux/screenshots/`

Start:

```bash
python3 prototypes/student_profile_ux/main.py
```

Der Prototyp demonstriert beide Varianten, neun Profilzustände, lokale Navigation, Kompetenz-Disclosure, Beobachtungsdetails, Dokumentstatus, Revisionen, LEG und historische Referenzen. Variante A deckt zusätzlich die Orientierungskarte mit genau drei Änderungen, mehr als drei qualifizierenden Änderungen, fachübergreifender Auswahl und vollständig leerem Zustand ab.

## 10. Screenshots

Die bisherigen Referenzbilder bleiben als verworfene Zwischenstände erhalten. Die Orientierungskarte von Variante A ist dokumentiert durch:

- `screenshots/variant-a-recognizable-three-1400x900.png`
- `screenshots/variant-a-recognizable-cross-subject-1400x900.png`
- `screenshots/variant-a-recognizable-1180x760.png`
- `screenshots/variant-a-recognizable-empty-1180x760.png`

## 11. Bewusst nicht umgesetzt

- keine produktive Schülerprofiländerung
- keine neue globale Navigation
- keine SQLite-, Repository-, Adapter- oder produktive ViewModel-Anbindung
- keine Datenbankmigration oder Datenmodelländerung
- keine neue Kompetenzstatusberechnung
- keine automatische Auswahl einer pädagogisch wichtigen Kompetenz
- keine Fachmittelwerte, Scores, Rankings, Prozentleistung oder automatische Trendinterpretation
- keine Bericht-/LEG-Architekturänderung
- keine finale PDF-Funktion oder Dokumentartefaktverwaltung
- keine echte Dateioperation
- keine Änderung produktiver Tests
- kein Staging und kein Commit

## 12. Risiken der späteren produktiven Übertragung

1. Die Eventherkunft und das Datum einer tatsächlichen Statusänderung brauchen einen bestätigten produktiven Read-Contract; die UI darf sie nicht aus uneinheitlichen Quellen erraten.
2. Zu entscheiden ist, ob historische Statusänderungen in die drei neuesten Entwicklungen einfließen oder in einem getrennten Lesekontext bleiben.
3. Der aktuelle Überblick enthält automatisch interpretierende Formulierungen. Eine visuelle Portierung darf diese nicht unbemerkt als Dashboardwahrheit übernehmen.
4. Das Profil benötigt echten Report-/Revisions-/LEG-Status aus einer reinen Leseprojektion; direkte Adapteraufrufe pro Karte oder SQLite-Zugriffe im Screen wären falsch.
5. Mehrere Bericht- oder LEG-Drafts müssen neutral zusammengefasst werden; der Profilüberblick darf keinen beliebigen Draft als fachlich maßgeblich auswählen.
6. Historische Kompetenz- und Beobachtungsreferenzen müssen in Profil, Bericht und LEG unterschiedlich, aber konsistent behandelt werden.
7. Jede zeitliche Verbindung in der Orientierungskarte braucht eine gleichwertige textliche Accessibility-Repräsentation und Tastaturzugang zu den realen Ereignissen.
8. Bei 1180 × 760 dürfen Filter nicht zu horizontalem Scroll oder unsichtbaren Pflichtaktionen führen.
9. Der aktuelle Berichtstab ist fachlich überholt, besitzt aber Tests und Text-Exportfunktionen. Seine spätere Ablösung braucht eine explizite Product-Owner-Entscheidung und Regressionstrategie.
10. Vor einer produktiven Übertragung ist zu entscheiden, wie die belegverknüpfte Orientierungskarte mit Standardwidgets oder einer zentralen wiederverwendbaren, barrierearmen Komponente den Design-System-Vertrag erfüllt.

## 13. Vorschlag für einen kleinen späteren Umsetzungsschnitt

Ein erster produktiver Schnitt sollte ausschließlich den Profilüberblick von Variante A umsetzen:

1. Product Owner bestätigt Variante A, Auswahlregel, Sortierung, Maximalzahl drei und den Einstieg `Alle Entwicklungen ansehen`.
2. Governance-Dokumente in der vorgeschriebenen Reihenfolge aktualisieren; keine neue Tabelle und kein neuer Schreibprozess.
3. Vorhandenen Profil-Read-Pfad um eine reine displayfertige Komposition für:
   - Kindkontext
   - konkrete Kompetenzen mit datierten Evidenzpunkten, Herkunft und Datum der jüngsten tatsächlichen Statusänderung
   - Dokumentationscounts und offene Fächer
   - neueste drei Beobachtungen
   - Report-/Revisions-/LEG-Kurzstatus
   ergänzen.
4. Nur den lokalen `Überblick` in `StudentProfileScreen` nach Variante A umbauen.
5. Bestehende Tabs, Beobachtungsliste, Kompetenz-Cockpit, Dokumente, Shell-Signale und produktive Bericht-/LEG-Dialoge unverändert lassen.
6. Neue fokussierte Tests für Datenherkunft, keine Statusneuberechnung, Accessibility der Orientierungskarte, 1400 × 900, 1180 × 760, Reduced Motion und Erhalt aller bestehenden Profileinstiege ergänzen.

## 14. Manueller Prüfblock für Laura

- Ist innerhalb weniger Sekunden verständlich, was sich verändert hat?
- Sind Kompetenz, früherer Stand, neuer Stand und Zeitraum klar?
- Ist die Verbindung zum dokumentierten Ereignis nachvollziehbar?
- Sind maximal drei Änderungen eine passende Menge?
- Wirkt die Karte ruhig oder weiterhin überladen?
- Sind die Einträge bei 1180 × 760 vollständig lesbar?
- Fehlt eine Information, die für die tägliche Arbeit notwendig ist?
- Wird die Darstellung fälschlich als Bewertung oder automatischer Trend verstanden?

Dieser Schnitt erzeugt bereits den gewünschten Schülerdashboard-Charakter, ohne gleichzeitig Kompetenzdetail, Beobachtungsworkflow, Bericht, LEG oder Persistenz umzubauen.
