"""Explicit completeness and freshness rules for the parent competency export."""

TOKENS = frozenset(("--", "-", "+", "++"))


def pending_competency_pdf_rows(model):
    return tuple((subject, row) for subject in model.subjects for row in subject.rows
                 if row.rating not in TOKENS)


def validate_competency_pdf_ready(model):
    if not model.subjects or not any(subject.rows for subject in model.subjects):
        raise ValueError("Keine aktuellen Kompetenzen vorhanden.")
    if pending_competency_pdf_rows(model):
        raise ValueError("Bitte für alle aktuellen Kompetenzen einen Entwicklungsstand auswählen.")


def validate_competency_pdf_completion(prepared, current, selections):
    if prepared != current:
        raise ValueError("Der Kompetenzstand wurde geändert. Bitte den Export erneut öffnen.")
    pending = pending_competency_pdf_rows(current)
    expected = {row.competency_id for _, row in pending}
    if not expected or "" in expected or len(expected) != len(pending):
        raise ValueError("Die Kompetenzauswahl ist nicht eindeutig oder bereits vollständig.")
    if set(selections) != expected or any(value not in TOKENS for value in selections.values()):
        raise ValueError("Bitte für alle offenen Kompetenzen eine gültige Auswahl treffen.")
