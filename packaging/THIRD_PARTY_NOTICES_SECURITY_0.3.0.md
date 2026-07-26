# Drittanbieterhinweise – interner Security-RC 0.3.0

Der interne macOS-arm64-Testbuild enthält zusätzlich zum bisherigen
Anwendungsbundle die nachstehenden Laufzeiten für den standardmäßig
deaktivierten, markergebundenen Security-Integrationstest:

| Komponente | Version | Lizenz / Einordnung |
|---|---:|---|
| PyNaCl | 1.6.2 | Apache-2.0 |
| libsodium | mit PyNaCl 1.6.2 gebündelt | ISC |
| sqlcipher3 | 0.6.2 | MIT |
| SQLCipher Community | 4.12.0 | BSD-style; nur interner Gate-On-Testpfad |
| cryptography | 49.0.0 | Apache-2.0 oder BSD-3-Clause |
| cffi | 2.0.0 | MIT |

Die vollständigen, aus den installierten Distributionen übernommenen
Lizenztexte liegen in den jeweiligen Unterordnern dieses Verzeichnisses.
PySide6/Shiboken6/Qt, PyInstaller, ReportLab, Pillow und Sparkle bleiben
Bestandteile des bisherigen Buildvertrags. Sparkles Lizenztext wird weiterhin
separat mit dem offiziellen, hashgeprüften Framework gebündelt.

Dieser Hinweis ist keine Freigabe einer produktiven Verschlüsselung. Der
SQLCipher-4.17.0-Produktzielstand, Windows-Paketierung, Developer-ID-Signierung
und Apple-Notarisierung bleiben getrennte Gates.
