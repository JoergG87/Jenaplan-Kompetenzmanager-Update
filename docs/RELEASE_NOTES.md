# Jenaplan-Kompetenzmanager 0.3.0 – Interner Security-Release-Candidate

Dieser Stand dient ausschließlich der internen technischen Abnahme.

- Der normale Produktpfad bleibt unverändert bei lokaler SQLite-Datenbank,
  bestehender Dokumentablage und ZIP-v1-Backup/Restore.
- Die neue Verschlüsselungsintegration ist standardmäßig deaktiviert, besitzt
  keinen Schalter in der App und führt keine automatische Migration aus.
- SQLCipher sowie verschlüsselte Dokument- und Backupcontainer werden nur in
  einem privaten, markergebundenen technischen Testbestand geprüft.
- Der produktive Support-Reset bleibt der beaufsichtigte Ausnahmeweg; ein
  Passwortwechsel oder Support-Reset rotiert keine Datenverschlüsselungskeys.
- Windows, Developer-ID-Signierung, Apple-Notarisierung, physische Touch ID,
  Produkt- oder Pilotmigration und ein öffentlicher Release sind nicht
  freigegeben.

Die Bezeichnung „Security-Release-Candidate“ ist keine Aussage über
Datenschutzkonformität, sichere physische Löschung oder Schutz vor einem
kompromittierten Benutzerprozess.
