# Drittanbieterhinweise – macOS-Pilot 0.5.0 / Build 405

Der Dateiname bleibt als bestehender Packaging-Vertrag erhalten. Die folgenden
Angaben beschreiben die tatsächlich im Build-405-Bundle vorhandenen
Sicherheitslaufzeiten. Der frühere interne Build-303-Teststand mit SQLCipher
4.12 ist historische Entwicklung und kein zweiter aktueller Provider.

| Komponente | Version | Lizenz / Einordnung |
|---|---:|---|
| PyNaCl | 1.6.2 | Apache-2.0 |
| libsodium | mit PyNaCl 1.6.2 gebündelt | ISC |
| sqlcipher3 | 0.6.2+jkm.sqlcipher4170.1 | LicenseRef-zlib; tatsächlicher zlib-artiger Quelldistributionstext, keine MIT-Behauptung |
| SQLCipher Community | 4.17.0 | BSD-3-Clause-artiger Originaltext; SQLite 3.53.3 / CommonCrypto |
| cryptography | 49.0.0 | Apache-2.0 oder BSD-3-Clause |
| cffi | 2.0.0 | MIT |

Die vollständigen, aus den installierten Distributionen übernommenen
Lizenztexte liegen in den jeweiligen Unterordnern dieses Verzeichnisses.
PySide6/Shiboken6/Qt, PyInstaller, ReportLab, Pillow und Sparkle bleiben
Bestandteile des bisherigen Buildvertrags. Sparkles Lizenztext wird weiterhin
separat mit dem offiziellen, hashgeprüften Framework gebündelt.

Die drei Originaltexte für Binding, SQLCipher und SQLite liegen außerdem in
`sqlcipher3-0.6.2+jkm.sqlcipher4170.1.dist-info/licenses/`. Details und
Quellbindung stehen im benachbarten
`THIRD_PARTY_NOTICES_SQLCIPHER_4_17_MACOS.md`.

Die Dokumentationsrevision ändert keine Abhängigkeit oder Originallizenz.
Dieser Hinweis behauptet weder eine rechtliche Freigabe noch ein vollständiges
SBOM-/CVE-Audit. Build 405 ist im qualifizierten Pilotpfad ad-hoc signiert;
Developer-ID-Signierung und Apple-Notarisierung werden nicht behauptet.
Eine Windows-Produktfreigabe besteht nicht.
