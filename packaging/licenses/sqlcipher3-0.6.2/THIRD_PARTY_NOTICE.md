# Drittanbieterhinweise – SQLCipher-4.17-macOS-arm64-Buildbasis

Diese Hinweise gelten ausschließlich für das temporär gebaute, nicht im
Repository gespeicherte Wheel. Sie aktivieren SQLCipher weder im Produkt noch
im Startup und ersetzen keine rechtliche Freigabe.

| Komponente | Exakter Stand | Lizenz / Einordnung |
|---|---:|---|
| SQLCipher Community | 4.17.0, Commit `810db22f575ee7cf94ea96a3e91622b5fcece3dc` | BSD-3-Clause-artig; Copyright 2025 ZETETIC LLC |
| SQLite in SQLCipher | 3.53.3 | Public Domain; siehe `SQLITE_LICENSE.md` der SQLCipher-Quelle |
| sqlcipher3 | 0.6.2, Commit `14fc2632676b20011e0bba64fdda49763a2dd2ec`; lokal als `0.6.2+jkm.sqlcipher4170.1` markiert | zlib-artiger Text aus der exakten Quelldistribution |
| CommonCrypto | Systemframework des verwendeten macOS SDK | Betriebssystemkomponente; kein Framework und kein Quellcode werden in das Wheel kopiert |

Die Binding-Metadaten der unveränderten Quelldistribution nennen `MIT`, ihre
mitgelieferte Datei `LICENSE` enthält jedoch den zlib-artigen Drei-Punkte-Text.
Der kontrollierte Build übernimmt den tatsächlichen Lizenztext, kennzeichnet
die abgeleitete lokale Version und setzt die Metadaten auf
`LicenseRef-zlib`. Er behauptet keine MIT-Lizenz.

Das Wheel enthält zugänglich:

- `LICENSE` aus `sqlcipher3` 0.6.2;
- `SQLCIPHER_LICENSE.md` aus SQLCipher 4.17.0;
- `SQLITE_LICENSE.md` aus SQLCipher 4.17.0 mit ausschließlich entferntem
  Zeilenend-Whitespace;
- diesen Drittanbieterhinweis als `THIRD_PARTY_NOTICE.md`.

Quell- und Lizenzhashes sowie sämtliche Buildflags sind in
`packaging/sqlcipher_4_17_macos_arm64_sources.json` gebunden. Eine spätere
Produktdistribution benötigt weiterhin SBOM-/CVE-Pflege, Paketierungsprüfung
und ausdrückliche Freigabe.
