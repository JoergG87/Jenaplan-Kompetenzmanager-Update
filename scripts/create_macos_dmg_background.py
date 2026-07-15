"""Create the quiet branded background used by the macOS pilot DMG."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 700
HEIGHT = 500


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    path = Path("/System/Library/Fonts/Supplemental") / name
    return ImageFont.truetype(str(path), size=size)


def create_background(output_path: Path, *, version: str) -> Path:
    """Render one deterministic Finder-window background."""
    image = Image.new("RGB", (WIDTH, HEIGHT), "#F5F7FB")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((30, 28, 670, 482), radius=28, fill="#FFFFFF")
    draw.text(
        (350, 62),
        "Jenaplan-Kompetenzmanager",
        font=_font(27, bold=True),
        fill="#203148",
        anchor="mm",
    )
    draw.text(
        (350, 96),
        f"Pilotversion {version}",
        font=_font(15),
        fill="#66758A",
        anchor="mm",
    )
    draw.text(
        (350, 130),
        "App auf Programme ziehen",
        font=_font(18, bold=True),
        fill="#355A7A",
        anchor="mm",
    )
    for center_x in (175, 525):
        draw.rounded_rectangle(
            (center_x - 78, 160, center_x + 78, 350),
            radius=22,
            fill="#F7FAFD",
            outline="#DCE5EE",
            width=2,
        )
    draw.line((292, 235, 408, 235), fill="#6D90AA", width=5)
    draw.polygon(((408, 235), (390, 224), (390, 246)), fill="#6D90AA")

    draw.rounded_rectangle(
        (270, 306, 430, 472),
        radius=18,
        fill="#F2F6FA",
        outline="#DCE5EE",
        width=2,
    )
    draw.text(
        (350, 324),
        "Vor dem ersten Start",
        font=_font(14, bold=True),
        fill="#355A7A",
        anchor="mm",
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    create_background(args.output, version=args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
