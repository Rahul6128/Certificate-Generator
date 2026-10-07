"""Draws a recipient's details onto the fixed certificate template.

The template (app/templates/certificate_template.png) is just the border +
title + the gold divider line where the name goes. We open it fresh for
every certificate so one generation can't bleed into another, write the
name + extra text on top, and save a PNG per recipient.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from app.config import TEMPLATE_PATH, STORAGE_DIR

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _font(size: int, bold: bool = False):
    name = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    path = f"{FONT_DIR}/{name}"
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # fallback if the font isn't on the box - still generates something usable
        return ImageFont.load_default()


def _centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, width: int, fill="#1a1a1a"):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((width - w) / 2, y), text, font=font, fill=fill)


class CertificateGenerationError(Exception):
    """Raised when we can't produce a certificate for a given recipient."""


def generate_certificate(certificate_id: str, name: str, extra_text: str | None) -> Path:
    if not TEMPLATE_PATH.exists():
        raise CertificateGenerationError(f"template missing at {TEMPLATE_PATH}")

    try:
        img = Image.open(TEMPLATE_PATH).convert("RGB")
    except Exception as exc:
        raise CertificateGenerationError(f"could not open template: {exc}") from exc

    draw = ImageDraw.Draw(img)
    width = img.width

    name_font = _font(52, bold=True)
    body_font = _font(26)

    # name sits just above the divider line drawn into the template at y=520
    _centered(draw, 440, name.strip(), name_font, width)
    if extra_text:
        _centered(draw, 560, extra_text.strip(), body_font, width, fill="#444")

    out_path = STORAGE_DIR / f"{certificate_id}.png"
    try:
        img.save(out_path)
    except OSError as exc:
        raise CertificateGenerationError(f"could not save certificate file: {exc}") from exc

    return out_path
