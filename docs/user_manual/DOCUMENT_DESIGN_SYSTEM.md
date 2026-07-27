# Dokumentendesign für Nutzerunterlagen

## Zweck

Dieses Designsystem steuert die aus dem Repository erzeugten A4-PDFs für
Lehrkräfte, schulische technische Betreuung sowie Pilot- und
Abnahmeunterlagen. Es beschreibt ausschließlich Darstellung und Leseführung;
es ändert keine Produkt-, Sicherheits- oder Releaseaussage.

## Zielgruppen und Informationsdichte

| Zielgruppe | Unterlagen | Informationsdichte | Ton und visuelle Gewichtung |
|---|---|---|---|
| Lehrkräfte | Schnellstart, Erste Schritte, Benutzerhandbuch, Backup | niedrig bis mittel | ruhig, handlungsorientiert, große Schritte und gut lesbare Bilder |
| Technische Betreuung | Installation, Support-Reset, Sicherheit und Verschlüsselung | mittel bis hoch | sachlich, präzise, Voraussetzungen, Kontrollpunkte und Stop-Bedingungen sichtbar |
| Pilot und Abnahme | Pilotinstallation, Release Notes, bekannte Grenzen | mittel | transparent, kompakt, mit klarer Trennung von Stand, Grenzen und nächsten Prüfungen |

## Gestaltungsgrundlagen

- **Format:** A4, 20 mm unten und 22 mm an den übrigen Rändern.
- **Schrift:** Arial und Arial Bold aus der macOS-Systeminstallation. Keine
  zusätzliche Schriftdatei ist erforderlich.
- **Typografie:** Titel 26 pt, Kapitel 18 pt, Zwischenüberschrift 13 pt,
  Fließtext 10,2 pt bei 14,6 pt Zeilenabstand, Bildunterschrift 8,6 pt.
- **Farben:** Dunkelblau `#203148` für Text, Produktblau `#355A7A` für
  Orientierung, helle Blaufläche `#F2F6FA` für neutrale Hinweise und
  Trennlinien `#DCE5EE`. Positive Sicherheits- und Kontrollhinweise verwenden
  eine zurückhaltende Grünfläche; echte Risiken eine warme, dezente
  Warnfläche. Jede Box benennt ihren Zweck zusätzlich als Text und bleibt
  dadurch auch in Graustufen verständlich.
- **Rhythmus:** Kurze Absätze, klarer Abstand vor Überschriften, keine
  isolierten Überschriften am Seitenende und keine ungerahmten, an den Text
  gedrängten Tabellen oder Bilder.

## Wiederverwendbare Bausteine

1. **Titelblatt:** Produktname, Dokumenttitel, Zielgruppe, Version, Build,
   Dokumentstand und Status in einem zurückhaltenden Metadatenblock.
2. **Kompakter Dokumentkopf:** für kurze Anleitungen statt eines separaten
   Titelblatts.
3. **Kopf- und Fußzeile:** Kurztitel mit aktuellem Kapitel sowie Produkt,
   Version/Build, Dokumentstand und Seitenzahl.
4. **Schrittfolge:** nummerierte, gut umbrochene Handlungszeilen mit einer
   abgesetzten Schrittnummer.
5. **Hinweisboxen:** `HINWEIS`, `TIPP`, `SICHERHEIT`, `VORAUSSETZUNG`,
   `KONTROLLE`, `FEHLERBEHEBUNG` und `WARNUNG`. Die Auszeichnung erfolgt in
   der Markdownquelle mit `> [!TYP]`; sie ist bewusst sparsam einzusetzen.
6. **Checkliste:** kompakte, klar getrennte Prüfpunkte für Vorbereitung oder
   Abschluss.
7. **Tabellen:** klare Kopfzeile, adaptive Spaltenbreite, wiederholte
   Kopfzeile und ausreichend Innenabstand.
8. **Bilder:** einheitlicher Rahmen, dezente Fläche, feste Maximalgröße,
   Bildunterschrift direkt am Bild und kein verzerrtes Skalieren.

## Wartung

Die Implementierung liegt zentral in `scripts/build_pilot_documents.py`.
Dokumente verwenden nur die hier beschriebenen Markdown-Bausteine und werden
bei jeder Änderung vollständig als PDF erzeugt und visuell geprüft.
