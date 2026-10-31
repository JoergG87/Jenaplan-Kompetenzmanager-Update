# Pilot-Dokumentinventar

Stand: 1. November 2026 - 0.5.1 / Build 406. Build 405 ist im Pilotkanal
veröffentlicht und bleibt unverändert. Produktbasis: `ddaee98`.
Der neue Dokumentationskandidat wird über die bestehende Pipeline gebaut;
seine exakte Paketquelle steht im Releasemanifest. Keine Veröffentlichung.

## Wartbare Quellen und tatsächliche Auslieferung

Alle acht PDF-Profile erzeugt `scripts/build_pilot_documents.py` mit
`--named-for-build --extended-guides`. Version und Build werden zentral
eingesetzt. Das bestehende A4-Design bleibt erhalten.

| Quelle | PDF-Profil / Zielgruppe | Auslieferung und Öffnung |
|---|---|---|
| `docs/user_manual/USER_MANUAL_SOURCE.md` | Benutzerhandbuch / Lehrkräfte und Betreuung | Dokumentations-ZIP; kein eingebettetes App-Handbuch |
| `docs/PILOT_INSTALLATION_LEHRKRAFT.md` | Installationsanleitung / Lehrkräfte | Dokumentations-ZIP; im DMG zusätzlich `Installationsanleitung.pdf` |
| `docs/PILOT_FIRST_STEPS.md` | Erste-Schritte / Lehrkräfte | Dokumentations-ZIP und `Contents/Resources/pilot_guides/` im signierten App-Bundle; kein Produkt-PDF-Öffner verbunden (`Erste Schritte` öffnet die Qt-Orientierung) |
| `docs/PILOT_QUICKSTART_LEHRKRAEFTE.md` | Schnellstart-Lehrkraefte / Lehrkräfte | Dokumentations-ZIP |
| `docs/PILOT_BACKUP.md` | Backup-und-Wiederherstellung / Lehrkräfte und Betreuung | Dokumentations-ZIP |
| `docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md` | Sicherheit-und-Verschluesselung / Lehrkräfte und Betreuung | Dokumentations-ZIP |
| `docs/SUPPORT_RESET_OPERATIONS.md` | Support-Reset-Betriebsanleitung / Betreuung | Dokumentations-ZIP; V4-Resetgrenzen und V7-Sperre ausdrücklich erklärt |
| `docs/RELEASE_NOTES.md` | Release-Notes / alle Pilotbeteiligten | Dokumentations-ZIP; Quelle für gesonderte Release-/Updatehinweise |
| `docs/PILOT_INSTALLATION_MACOS.md` | kein weiteres PDF / technische Betreuung | Markdown in Dokumentations-ZIP; vertiefte Installations-, Wartungs- und Fehlerbehebung |
| `docs/SUPPORT_ASSISTANT_OPERATIONS.md` | kein weiteres PDF / Support | Markdown in Dokumentations-ZIP; getrenntes Supportwerkzeug, keine Schlüssel im Lehrkraftpaket |
| `docs/DATA_LIFECYCLE.md` | kein weiteres PDF / technische Betreuung | Technischer Vertrag in Dokumentations-ZIP; aktuelle Einordnung vor erhaltenen historischen Abschnitten |
| `docs/PILOT_DOCUMENT_INVENTORY.md` | dieses Inventar / Betreuung und Release | Markdown in Dokumentations-ZIP |
| `packaging/THIRD_PARTY_NOTICES_SECURITY_0.3.0.md` | vorhandener Dateiname bleibt Packaging-Vertrag | App-Bundle `third_party_licenses/` und Dokumentations-ZIP; aktuelle Build-406-Komponenten |
| `packaging/THIRD_PARTY_NOTICES_SQLCIPHER_4_17_MACOS.md` | Datenbankprovider und Lizenztexte | App-Bundle `third_party_licenses/` und Dokumentations-ZIP |
| `packaging/licenses/sqlcipher-4.17.0/` und `packaging/licenses/sqlcipher3-0.6.2/LICENSE` | Originaltexte / Betreuung | Originaltexte in Dokumentations-ZIP; Binding-/SQLCipher-/SQLite-Texte auch in Bundle-Distributionsmetadaten |
| `scripts/backup_macos_pilot.sh` | historische Backup-Hilfsdatei | bleibt erhalten; im Cipher-Produktpfad ausdrücklich gesperrt, kein empfohlenes Backupverfahren |

Das Standard-Buildskript erzeugte beim bisherigen Kandidaten fünf PDFs;
Sicherheit, Support Reset und Release Notes waren nur Markdown in der ZIP
oder im Review verfügbar. Das revidierte Release-Set enthält alle acht PDFs.
Technische Ergänzungen bleiben in vorhandenen Quellen, ohne paralleles Handbuch.

## Paketbindung und Gültigkeit alter Nachweise

Die Revision betrifft das Erste-Schritte-PDF im App-Bundle und das
Installations-PDF im DMG. Deshalb wird über `scripts/build_macos_pilot.sh`
ein neuer Kandidat erzeugt, regulär versiegelt und signiert. Kein signiertes
Paket wird nachträglich editiert. Der qualifizierte Ausgangskandidat unter
`release/output/0.5.1-build406-ddaee98594ec/` bleibt unverändert.

Separat veröffentlicht werden nach PO-Freigabe die vier konfigurierten Assets:
DMG, Dokumentations-ZIP, Prüfsummenliste und Releaseinventar. Die acht PDFs
liegen vollständig in der ZIP und lokal zusätzlich einzeln vor. Release Notes
liegen als PDF in der ZIP, als Markdown für GitHub und als signiertes HTML
für Sparkle vor. Manifest und Signaturbericht binden die endgültigen Bytes.

## Screenshots, Generatoren und PDF-Abnahme

`scripts/capture_user_manual_screenshots.py` erzeugt die verwendeten Qt-Bilder
mit ausschließlich synthetischem temporärem Bestand und aktuellen
V7-Projektionen. Unterrichtszeiten, Stammgruppen-/Mehrfachfachstunden,
A-/B-Wochen mit Einzelwochenkorrektur, Fachpflanzen und Migrationsdialoge erhalten gezielte
Abbildungen. Produktinstallation und vorhandene Schlüssel werden nicht geöffnet.
Die fachliche Oberfläche entspricht dem freigegebenen Code; die synthetische
Fixture ist kein Beleg für Paket-, Verschlüsselungs- oder Releasegates.

Abnahme umfasst die tatsächlich generierten PDF-Seiten, Textvollständigkeit,
Versionsangaben, Bildverweise, Links und visuelle Kontrolle von Umbruch,
Tabellen, Schrift und Lesbarkeit. Ergebnisse und Seitenzahlen stehen im
Revisionsbericht und in den zugehörigen Prüfdateien im neuen Kandidatenordner.

## Ausgeschlossene historische Unterlagen

| Bestand | Einordnung |
|---|---|
| `docs/user_manual/*Build-302*.pdf` | acht PDFs: historisch, nicht übergeben; unverändert und nicht in der Build-406-ZIP |
| `docs/SECURITY_RELEASE_0_3_0.md` | historischer Build-303-Nachweis, keine aktuelle Bedienanleitung |
| `docs/ENCRYPTION_AND_SUPPORT_RESET_PREANALYSIS.md` | historische Voranalyse, kein aktueller Funktionsvertrag |
| `docs/LAURA_PILOTTEST.md`, `docs/laura_pilottest_feedback.csv`, `scripts/build_laura_pilot_package.py` | frühere Testübergabe; alter portabler Laura-Testdatenpfad im Cipher-Produktbuild gesperrt |
| `docs/lehrplan/quellen/*.pdf` | fachliche externe Referenzen; kein Installations-/Lehrkraftpaket |
| `legacy/excel/` | archivierter Referenz-/Exportpfad; kein Bestandteil dieses Auftrags |

Historische Technikabschnitte dokumentieren ihren damaligen Stand. Sie werden
nicht rückwirkend auf V7 umgeschrieben und ersetzen die aktuellen
Build-406-Anleitungen nicht.
