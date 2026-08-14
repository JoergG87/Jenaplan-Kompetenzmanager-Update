"""Current pilot-document source, render, and PDF safety contracts."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

from PIL import Image
from pypdf import PdfReader

from src.version import APP_BUILD_VERSION, APP_VERSION


ROOT = Path(__file__).resolve().parents[1]
CURRENT_SOURCES = (
    ROOT / "docs/user_manual/USER_MANUAL_SOURCE.md",
    ROOT / "docs/PILOT_INSTALLATION_LEHRKRAFT.md",
    ROOT / "docs/PILOT_FIRST_STEPS.md",
    ROOT / "docs/PILOT_QUICKSTART_LEHRKRAEFTE.md",
    ROOT / "docs/PILOT_BACKUP.md",
    ROOT / "docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md",
    ROOT / "docs/SUPPORT_RESET_OPERATIONS.md",
    ROOT / "docs/RELEASE_NOTES.md",
)
EXPECTED_SUFFIXES = (
    "Benutzerhandbuch",
    "Installationsanleitung",
    "Erste-Schritte",
    "Schnellstart-Lehrkraefte",
    "Backup-und-Wiederherstellung",
    "Sicherheit-und-Verschluesselung",
    "Support-Reset-Betriebsanleitung",
    "Release-Notes",
)


def _pdf_text(path: Path) -> str:
    reader = PdfReader(path)
    assert len(reader.pages) > 0
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_current_document_sources_use_version_placeholders_and_final_v4_truth() -> None:
    for source in CURRENT_SOURCES:
        text = source.read_text(encoding="utf-8")
        assert "{{PILOT_VERSION}}" in text
        assert "{{PILOT_BUILD}}" in text
        assert "0.4.0 / Build 400" not in text

    teacher_text = "\n".join(
        source.read_text(encoding="utf-8") for source in CURRENT_SOURCES[:5]
    )
    assert ".jkmebackup" in teacher_text
    assert "331 Kompetenzen" in teacher_text
    assert "ZIP-v1" not in teacher_text
    assert ".jkmbackup" not in teacher_text
    assert "App-Sperre ist keine Verschlüsselung" not in teacher_text
    assert "sechs Phasen" not in teacher_text


def test_current_manual_screenshots_are_present_and_use_final_v4_capture_contract() -> None:
    manual = (ROOT / "docs/user_manual/USER_MANUAL_SOURCE.md").read_text(
        encoding="utf-8"
    )
    referenced = {
        ROOT / "docs/user_manual" / relative
        for relative in re.findall(r"\((screenshots/[^)]+\.png)\)", manual)
    }
    assert referenced
    assert all(path.is_file() for path in referenced)
    assert all("Build-302" not in path.name for path in referenced)
    for path in referenced:
        with Image.open(path) as screenshot:
            assert screenshot.format == "PNG"
            assert screenshot.width >= 640
            assert screenshot.height >= 120
            screenshot.verify()
    with Image.open(
        ROOT / "docs/user_manual/screenshots/25_student_subject_selection.png"
    ) as subject_selection:
        assert subject_selection.width >= 1200
        assert subject_selection.height >= 800

    capture_source = (ROOT / "scripts/capture_user_manual_screenshots.py").read_text(
        encoding="utf-8"
    )
    assert ".jkmebackup" in capture_source
    assert ".jkmbackup" not in capture_source
    assert "23_about_build_302.png" not in capture_source
    assert "24_first_steps.png" in capture_source
    assert "25_student_subject_selection.png" in capture_source


def test_teacher_guides_explain_individual_student_subject_workflow() -> None:
    first_steps = (ROOT / "docs/PILOT_FIRST_STEPS.md").read_text(encoding="utf-8")
    quickstart = (ROOT / "docs/PILOT_QUICKSTART_LEHRKRAEFTE.md").read_text(
        encoding="utf-8"
    )
    manual = (ROOT / "docs/user_manual/USER_MANUAL_SOURCE.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((first_steps, quickstart, manual))
    normalized_first_steps = " ".join(first_steps.split())
    normalized_quickstart = " ".join(quickstart.split())
    normalized_manual = " ".join(manual.split())

    for guide in (normalized_first_steps, normalized_quickstart, normalized_manual):
        assert "Schüler" in guide
        assert "Profil öffnen" in guide
        assert "Überblick" in guide
        assert "Fächer für die Dokumentation" in guide
        assert "Aufklappen" in guide

    for visible_label in (
        "Profil öffnen",
        "Fächer für die Dokumentation",
        "Aufklappen",
        "Für dieses Kind individuell festlegen",
        "Speichern",
        "Fächer",
        "Weitere Fächer",
    ):
        assert visible_label in combined
    for subject in (
        "EPU",
        "Deutsch",
        "Mathematik",
        "Kreatives Gestalten",
        "Sport",
        "Ethik",
        "Religion",
        "Musik",
        "Englisch",
        "Schulgarten",
    ):
        assert subject in normalized_first_steps
        assert subject in normalized_quickstart
        assert subject in normalized_manual

    assert "Selbst- und Sozialkompetenz" in combined
    assert "Arbeits-/Lernkompetenz" in combined
    assert "immer verfügbar" in combined
    assert "keine harte fachliche Berechtigungsgrenze" in normalized_first_steps
    assert "keine Berechtigungsgrenze" in normalized_quickstart
    assert "keine harte fachliche Berechtigungsgrenze" in normalized_manual
    assert "leere individuelle Auswahl bleibt leer" in normalized_first_steps
    assert "leere individuelle Auswahl bleibt leer" in normalized_quickstart
    assert "nicht automatisch" in normalized_manual
    assert "25_student_subject_selection.png" in manual

    prohibited_current_claims = (
        "Fächer gelten für alle Schüler gemeinsam",
        "überfachliche Bereiche müssen als Fächer ausgewählt werden",
        "Selbst-/Sozialkompetenz im Stundenplan",
        "Arbeits-/Lernkompetenz im Stundenplan",
    )
    assert not any(claim in combined for claim in prohibited_current_claims)


def test_all_current_pilot_document_profiles_render_parse_and_scan_cleanly(
    tmp_path: Path,
) -> None:
    output = tmp_path / "review-pdfs"
    command = (
        sys.executable,
        "scripts/build_pilot_documents.py",
        "--version",
        APP_VERSION,
        "--build-version",
        APP_BUILD_VERSION,
        "--document-date",
        "14. August 2026",
        "--output-dir",
        str(output),
        "--named-for-build",
        "--extended-guides",
        "--installation-source",
        "docs/PILOT_INSTALLATION_LEHRKRAFT.md",
        "--manual-source",
        "docs/user_manual/USER_MANUAL_SOURCE.md",
        "--first-steps-source",
        "docs/PILOT_FIRST_STEPS.md",
        "--quickstart-source",
        "docs/PILOT_QUICKSTART_LEHRKRAEFTE.md",
        "--backup-source",
        "docs/PILOT_BACKUP.md",
        "--security-source",
        "docs/SICHERHEIT_UND_VERSCHLUESSELUNG.md",
        "--support-reset-source",
        "docs/SUPPORT_RESET_OPERATIONS.md",
        "--release-notes-source",
        "docs/RELEASE_NOTES.md",
        "--icon",
        "assets/app_icon.png",
    )
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)

    expected = {
        output
        / (
            f"Jenaplan-Kompetenzmanager-{APP_VERSION}-Build-"
            f"{APP_BUILD_VERSION}-{suffix}.pdf"
        )
        for suffix in EXPECTED_SUFFIXES
    }
    assert set(output.glob("*.pdf")) == expected

    extracted = {path.name: _pdf_text(path) for path in expected}
    combined = "\n".join(extracted.values())
    assert "{{" not in combined and "}}" not in combined
    assert "/Users/" not in combined
    assert "/private/tmp/" not in combined
    assert "BEGIN PRIVATE KEY" not in combined
    assert "BEGIN ENCRYPTED PRIVATE KEY" not in combined
    assert "JKM-SR1." not in combined
    assert "Laura Gehrke" not in combined

    manual = next(text for name, text in extracted.items() if "Benutzerhandbuch" in name)
    first_steps = next(
        text for name, text in extracted.items() if "Erste-Schritte" in name
    )
    quickstart = next(
        text for name, text in extracted.items() if "Schnellstart-Lehrkraefte" in name
    )
    security = next(
        text for name, text in extracted.items() if "Sicherheit-und-Verschluesselung" in name
    )
    installation = next(
        text for name, text in extracted.items() if "Installationsanleitung" in name
    )
    release_notes_path = next(
        path for path in expected if "Release-Notes" in path.name
    )
    release_note_pages = tuple(
        page.extract_text() or "" for page in PdfReader(release_notes_path).pages
    )
    subject_structure_page = next(
        page for page in release_note_pages if "Fachliche Struktur" in page
    )
    assert "Selbst- und Sozialkompetenz" in subject_structure_page
    assert ".jkmebackup" in manual
    assert "Final V4" in security
    assert "SQLCipher 4.17" in security
    assert "nicht beliebig auf jedem Mac" in installation
    assert "keine allgemeine Geräteportabilität" in installation

    for guide in (manual, first_steps, quickstart):
        normalized = " ".join(guide.split())
        for term in (
            "Profil öffnen",
            "Überblick",
            "Aufklappen",
            "individuell festlegen",
            "EPU",
            "Kreatives Gestalten",
            "Selbst- und Sozialkompetenz",
            "Arbeits-/Lernkompetenz",
            "immer verfügbar",
            "Weitere Fächer",
            "leere individuelle Auswahl",
        ):
            assert term in normalized
    assert "keine harte fachliche Berechtigungsgrenze" in " ".join(manual.split())
    assert "keine harte fachliche Berechtigungsgrenze" in " ".join(
        first_steps.split()
    )
    assert "keine Berechtigungsgrenze" in " ".join(quickstart.split())


def test_historical_build_302_pdfs_are_not_current_generator_outputs() -> None:
    historical = tuple((ROOT / "docs/user_manual").glob("*Build-302*.pdf"))
    assert len(historical) == 8
    inventory = (ROOT / "docs/PILOT_DOCUMENT_INVENTORY.md").read_text(
        encoding="utf-8"
    )
    assert "historisch, nicht übergeben" in inventory
    assert all("Build-302" in path.name for path in historical)
