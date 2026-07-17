# Laura-Pilottest

## Zweck

Der Pilottest prüft den Jenaplan-Kompetenzmanager mit ausschließlich künstlichen Testdaten aus der Sicht einer Lehrkraft. Im Mittelpunkt stehen Verständlichkeit, ruhige Bedienung, fachlich nachvollziehbare Zustände und alltagstaugliche Wege – nicht eine vollständige technische Abnahme.

## Führende Testdatei und versionierte Testfallquelle

Die einzige führende Pilot-Testdatei für Laura heißt
`Pilottest_Laura_Schuelerprofil_Variante_A.xlsx`. Der lokale Originalpfad wird
nicht in Release-Dokumente oder Pakete geschrieben; für den Build wird er über
`LAURA_TEST_WORKBOOK` übergeben.

Sie enthält den ausführbaren Testplan, konkrete Schritte und Erwartungen im
Blatt `Testhinweise`, die Ergebniserfassung sowie das Feedbackblatt. Neue
Rückmeldungen werden dort eingetragen; die frühere CSV dient nicht mehr als
führender Feedbackweg. Dieses Dokument ist die versionierte kanonische Quelle
für noch nicht in die Arbeitsmappe übernommene Testfallergänzungen. Die
Arbeitsmappe wird erst im ausdrücklich beauftragten Excel-Schritt daraus
aktualisiert; bestehende Ergebnisse werden dabei nicht überschrieben.

## Vorgemerkt für die nächste Testmappen-Aktualisierung

- **LEG:** Prüfen, ob Vorschau beziehungsweise Gesprächsführung während der
  Bearbeitung ausreichend sichtbar und erreichbar sind. Status: offen, reale
  Laura-Prüfung noch nicht durchgeführt.

## Testablauf

1. Künstliche Testdaten erzeugen und die App starten:

   ```bash
   python3 scripts/seed_test_data.py --reset
   python3 -m src.desktop_app.main
   ```

2. Die Arbeitsmappe öffnen und die Fälle im Blatt `Testplan` in der vorgeschlagenen Reihenfolge bearbeiten. Detail-Schritte, erwartete Ergebnisse und Hinweise stehen im Blatt `Testhinweise` unter derselben Testnummer.

3. Im Testplan das Ergebnis auswählen. Auffälligkeiten einzeln im Blatt `Feedback` mit Testnummer, Kategorie, Beobachtung, Erwartung und tatsächlichem Verhalten erfassen.

4. Für die Profilfälle bewusst Kinder mit vielen, wenigen, fehlenden und historischen Dokumentationen wählen. Für Bericht- und LEG-Abschlussfälle nur künstliche Testdaten verwenden.

## Version und Stand

- Datei: `Pilottest_Laura_Schuelerprofil_Variante_A.xlsx`
- Stand: 15.07.2026
- Umfang: 65 Testfälle
- Schwerpunkt: Schülerprofil Variante A, Beobachtungen, Dashboard/Stundenplan, Berichtsdraft und Revisionen, finale Bericht-PDFs, LEG-Draft, LEG-Abschluss/Revision/PDF sowie historische und schreibgeschützte Ansichten.

## Hinweise für Laura

- Es werden keine echten Kindernamen, echten Dokumente oder personenbezogenen Daten verwendet.
- Ein Fehler, eine unklare Bedienung, ein Wunsch und eine Produktentscheidung sind unterschiedliche Rückmeldekategorien; bitte die passende Kategorie wählen.
- Screenshots oder genaue Bildschirmtexte helfen besonders bei Fehlern.
- Beim finalen PDF immer unterscheiden: Entwurfs-PDFs stammen aus einem bearbeitbaren Berichtsentwurf; finale PDFs ausschließlich aus der aktuellen unveränderlichen Revision.
- Bereits vorhandene, ältere Testmappen nicht zusammenführen. Sie bleiben als Archiv erhalten, aber neue Testläufe beginnen ausschließlich mit der führenden Datei.
