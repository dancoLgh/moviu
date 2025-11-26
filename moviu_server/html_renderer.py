"""Utilities to transform HTML payloads into printable raster images."""

from __future__ import annotations

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


DEFAULT_WIDTH = 576  # Typical ESC/POS printable width in pixels.
BACKGROUND_COLOR = "white"
FOREGROUND_COLOR = "black"
FONT_SIZE = 20
FONT = ImageFont.load_default()


def html_to_plain_text(html: str) -> str:
    """Convert HTML into a simple plain text representation."""

    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text(separator="\n")
    normalized = "\n".join(line.strip() for line in text.splitlines())
    return normalized.strip() or "(contenido vacío)"


def text_to_image(text: str, width: int = DEFAULT_WIDTH) -> Image.Image:
    """Render text into a Pillow image that fits ESC/POS width."""

    lines = []
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (width, 1000)))
    max_line_width = width - 20
    for paragraph in text.splitlines():
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            bbox = draw_dummy.textbbox((0, 0), candidate, font=FONT)
            if bbox[2] > max_line_width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        lines.append("")
    if not lines:
        lines = [""]
    line_height = FONT.getbbox("A")[3] + 8
    height = max(100, line_height * len(lines) + 20)
    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    y = 10
    for line in lines:
        draw.text((10, y), line, fill=FOREGROUND_COLOR, font=FONT)
        y += line_height
    return image


def html_to_image(html: str, width: int = DEFAULT_WIDTH) -> Image.Image:
    """High-level helper that turns HTML into a raster image."""

    text = html_to_plain_text(html)
    return text_to_image(text, width=width)
