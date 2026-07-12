"""Command-line entry point for the isolated Sprint 7E PDF engine prototype."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .demo_data import build_demo_report
    from .renderer import PdfRenderer
except ImportError:
    from demo_data import build_demo_report  # type: ignore[no-redef]
    from renderer import PdfRenderer  # type: ignore[no-redef]


DEFAULT_OUTPUT = Path("output/pdf/Sprint_7E_Lernentwicklungsbericht_Mara_Beispielkind.pdf")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render fictional neutral output data as a professional PDF."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output file (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = PdfRenderer().render(build_demo_report(), args.output)
    print(f"PDF erzeugt: {target.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
