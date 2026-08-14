# Pilot-Dokumentinventar

Stand: 14. August 2026

Dieses Inventar trennt aktuelle wartbare Pilotquellen von historischen
Releasebelegen. Aktuelle Review-PDFs werden ausschließlich mit
`scripts/build_pilot_documents.py --named-for-build --extended-guides` aus den
folgenden Quellen erzeugt.

| Quelle | Generator | PDF-Profil | Zielgruppe | Klassifikation |
|---|---|---|---|---|
| `docs/user_manual/USER_MANUAL_SOURCE.md` | `scripts/build_pilot_documents.py` | `Benutzerhandbuch` | Lehrkräfte, Stammdatenpflege, technische Betreuung | aktuell |
| `docs/PILOT_INSTALLATION_LEHRKRAFT.md` | derselbe | `Installationsanleitung` | Lehrkräfte, technische Betreuung | aktuell |
| `docs/PILOT_FIRST_STEPS.md` | derselbe | `Erste-Schritte` | Lehrkräfte | aktuell |
| `docs/PILOT_QUICKSTART_LEHRKRAEFTE.md` | derselbe | `Schnellstart-Lehrkraefte` | Lehrkräfte | aktuell |
| `docs/PILOT_BACKUP.md` | derselbe | `Backup-und-Wiederherstellung` | Lehrkräfte, technische Betreuung | aktuell |
| `docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md` | derselbe, `--extended-guides` | `Sicherheit-und-Verschluesselung` | Lehrkräfte, technische Betreuung, Releaseverantwortliche | aktuell |
| `docs/SUPPORT_RESET_OPERATIONS.md` | derselbe, `--extended-guides` | `Support-Reset-Betriebsanleitung` | technische Betreuung | aktuell intern |
| `docs/RELEASE_NOTES.md` | derselbe, `--extended-guides` | `Release-Notes` | Lehrkräfte, technische Betreuung | aktueller Reviewstand |
| `docs/PILOT_INSTALLATION_MACOS.md` | kein PDF | - | technische Pilotvorbereitung | aktuell |
| `docs/SUPPORT_ASSISTANT_OPERATIONS.md` | separates Supportpaket | `SUPPORT_ANLEITUNG.md` | Supportbetrieb | aktuell intern |
| `scripts/build_laura_pilot_package.py` (eingebettete README) | historischer Laura-Paketbuilder | `README.txt` | frühere Pilotübergabe | historisch; im Final-V4-Buildpfad gesperrt |
| `docs/SECURITY_RELEASE_0_3_0.md` | kein aktuelles PDF | - | Releasehistorie | historischer Build-303-Beleg |
| `docs/user_manual/*Build-302*.pdf` | frühere Generatorläufe | acht Build-302-PDFs | historische Nachvollziehbarkeit | historisch, nicht übergeben |
| `docs/lehrplan/quellen/*.pdf` | externe Primärquellen | Lehrplan-PDFs | Katalogarbeit | historisch/referenziell, kein Pilotpaket |

## Platzhalter und Screenshots

Alle acht aktuellen PDF-Quellen verwenden `{{PILOT_VERSION}}` und
`{{PILOT_BUILD}}`; der Generator löst beide Werte aus der zentral vorgegebenen
Version auf. `scripts/capture_user_manual_screenshots.py` erzeugt alle im
Handbuch und Backupguide verwendeten Qt-Abbildungen aus einem temporären,
synthetischen Datenbestand. Die aktuelle PDF-Erzeugung bindet keine
historische HTML-Oberfläche, Klartext-/Altbackupabbildung oder echte
Schülerdaten ein.

Die aktuelle Standardschiene des macOS-Builds erzeugt fünf Lehrkraft-PDFs.
Das vollständige Reviewset dieses Auftrags umfasst zusätzlich Sicherheit,
Support Reset und Release Notes. Reviewoutputs liegen unter einem eindeutigen
`/private/tmp`-Evidencepfad und sind keine final versionierten
Releaseartefakte. Historische Build-302-PDFs werden nicht überschrieben.
Der alte Laura-Testdatenpaketpfad mit ZIP-v1/`.jkmbackup` wird vom aktuellen
Final-V4-Build bereits bei der Argumentprüfung abgewiesen und gehört weder zum
Reviewset noch zu einer heutigen Pilotübergabe.
