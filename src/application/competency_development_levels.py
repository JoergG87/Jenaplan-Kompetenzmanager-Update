"""Shared plant-stage presentation; persisted rating tokens remain unchanged."""
DEVELOPMENT_LEVEL_LABELS = {
    "--": "Erste Erfahrungen",
    "-": "Mit Unterstützung",
    "+": "Kenntnisse meist anwenden",
    "++": "Eigenständig und sicher",
}
DEVELOPMENT_LEVEL_COMPACT_LABELS = {
    "--": "Erste\nErfahrungen",
    "-": "Mit\nUnterstützung",
    "+": "Kenntnisse meist\nanwenden",
    "++": "Eigenständig\nund sicher",
}
DEVELOPMENT_LEVEL_DESCRIPTIONS = {
    "--": "Du hast erste Erfahrungen gesammelt.",
    "-": "Du kannst dein Wissen mit Unterstützung anwenden.",
    "+": "Du kannst deine erworbenen Kenntnisse meist anwenden.",
    "++": "Du kannst das Erlernte eigenständig und sicher anwenden.",
}

DEVELOPMENT_LEVEL_LABELS_BY_PROFILE = {
    "standard": DEVELOPMENT_LEVEL_LABELS,
    "social": {"--": "Kaum vorhanden", "-": "Teilweise", "+": "Gut", "++": "Ausgeprägt"},
    "sport": {"--": "Erste Übungen", "-": "Übt noch", "+": "Meist", "++": "Sicher"},
}
DEVELOPMENT_LEVEL_DESCRIPTIONS_BY_PROFILE = {
    "standard": DEVELOPMENT_LEVEL_DESCRIPTIONS,
    "social": DEVELOPMENT_LEVEL_LABELS_BY_PROFILE["social"],
    "sport": {
        "--": "Du hast erste Übungen gemacht.",
        "-": "Du kannst das schon etwas und übst noch.",
        "+": "Du kannst das meist.",
        "++": "Du kannst das sicher.",
    },
}


def compact_development_level_label(label: str) -> str:
    """Wrap the actual profile label without substituting another meaning."""
    compact = {DEVELOPMENT_LEVEL_LABELS[token]: value
               for token, value in DEVELOPMENT_LEVEL_COMPACT_LABELS.items()}
    compact.update({"Kaum vorhanden": "Kaum\nvorhanden", "Erste Übungen": "Erste\nÜbungen"})
    return compact.get(label, label)
